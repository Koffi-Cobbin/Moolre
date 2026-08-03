"""
Inbound webhook/callback receiver (plan Section 6) — PLACEHOLDER.

Full implementation (Milestone 3) will:
    1. Store raw payload in WebhookEvent immediately (audit/replay)
    2. Validate shape via moolre_client.signing.validate_shape()
    3. Look up PaymentRequest by externalref, update status idempotently
    4. Fire a Django signal (payment_completed / payment_failed)
    5. Return 200 quickly; queue heavier follow-up work

Wired now (returning 501) purely so the URL exists and the go-live
checklist item "confirm webhook endpoint is publicly reachable over HTTPS"
(plan Section 11) has something real to point at during scaffolding.
"""

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST


@csrf_exempt
@require_POST
def payment_webhook(request):
    # TODO(milestone-3): implement per plan Section 6.
    return JsonResponse(
        {"error": "Payment webhook handling is not implemented yet (Milestone 3)."},
        status=501,
    )
