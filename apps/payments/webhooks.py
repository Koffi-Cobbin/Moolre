"""
Inbound webhook/callback receiver (plan Section 6).

Moolre's documented payment webhook has no signature header
(docs.moolre.com/ai/payment-webhook.md), so this handler follows the
"verify, don't trust" fallback explicitly recommended by both the plan
and Moolre's own webhooks guide: persist the raw payload immediately, then
re-fetch the authoritative status from `transact/status` rather than
trusting the callback body's `status`/`code` fields directly.

Flow (plan Section 6):
    1. Store raw payload in WebhookEvent immediately (audit/replay)
    2. Validate shape
    3. Look up PaymentRequest by externalref
    4. Re-verify via transact/status (signing.verify_via_status_check)
    5. Update status idempotently + fire payment_completed/payment_failed
    6. Return 200 quickly
"""

import json
import logging

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.moolre_client.exceptions import MoolreValidationError
from apps.moolre_client.signing import validate_shape, verify_via_status_check

from . import services
from .models import PaymentRequest, WebhookEvent

logger = logging.getLogger("payments.webhooks")


@csrf_exempt
@require_POST
def payment_webhook(request):
    try:
        payload = json.loads(request.body or b"{}")
    except ValueError:
        # Still log it -- an unparseable payload is exactly the kind of
        # thing you want in the audit trail (plan Section 6, step 1).
        WebhookEvent.objects.create(raw_payload={"raw_text": request.body.decode(errors="replace")})
        return JsonResponse({"error": "invalid JSON"}, status=400)

    # Step 1: persist immediately, before any processing.
    event = WebhookEvent.objects.create(raw_payload=payload)

    try:
        validate_shape(payload)
    except MoolreValidationError as exc:
        logger.warning("Malformed webhook payload (event %s): %s", event.id, exc)
        return JsonResponse({"error": str(exc)}, status=400)

    externalref = (payload.get("data") or {}).get("externalref")
    if not externalref:
        logger.warning("Webhook payload missing data.externalref (event %s)", event.id)
        return JsonResponse({"error": "missing data.externalref"}, status=400)

    try:
        payment_request = PaymentRequest.objects.get(externalref=externalref)
    except PaymentRequest.DoesNotExist:
        # Nothing local to reconcile against yet -- ack so Moolre doesn't
        # keep retrying, but don't mark this event processed.
        logger.warning("Webhook for unknown externalref %s (event %s)", externalref, event.id)
        return JsonResponse({"received": True}, status=200)

    # Step 4: "verify, don't trust" -- re-check status rather than trusting
    # the callback body outright.
    verify_via_status_check(externalref, status_check_fn=lambda _ref: services.check_payment_status(payment_request))

    event.verified = True
    event.processed = True
    event.save(update_fields=["verified", "processed"])

    return JsonResponse({"received": True}, status=200)
