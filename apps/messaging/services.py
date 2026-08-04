"""
Messaging (SMS + WhatsApp) service layer (plan Section 5).
"""

from __future__ import annotations

import uuid

from django.conf import settings
from django.utils import timezone

from apps.moolre_client.client import MoolreClient
from apps.moolre_client.exceptions import MoolreAPIError

from .models import SenderId, SmsMessage, WhatsAppMessage, WhatsAppTemplate


def _client() -> MoolreClient:
    return MoolreClient.from_settings(settings.MOOLRE)


# -- SMS ------------------------------------------------------------------------


def send_sms(senderid: SenderId, *, recipient: str, message: str, ref: str | None = None) -> SmsMessage:
    """Send a single SMS via `sms/send`. Writes a "pending" row first
    (plan Section 5), then updates it based on the (batch-shaped) response.
    """
    ref = ref or str(uuid.uuid4())
    sms = SmsMessage.objects.create(
        senderid=senderid, recipient=recipient, message=message, ref=ref
    )
    client = _client()
    try:
        response = client.sms.send(
            senderid=senderid.name, messages=[{"recipient": recipient, "message": message, "ref": ref}]
        )
    except MoolreAPIError as exc:
        sms.status = SmsMessage.Status.FAILED
        sms.raw_response = exc.raw_response
        sms.save()
        raise

    sms.raw_response = response
    sms.status = SmsMessage.Status.SENT
    sms.sent_at = timezone.now()
    sms.save()
    return sms


def send_bulk_sms(senderid: SenderId, *, messages: list[dict]) -> list[SmsMessage]:
    """Send several SMS in one API call. `messages`: list of
    {"recipient": str, "message": str, "ref": str (optional)}.
    """
    prepared = []
    for m in messages:
        prepared.append({**m, "ref": m.get("ref") or str(uuid.uuid4())})

    records = [
        SmsMessage.objects.create(
            senderid=senderid, recipient=m["recipient"], message=m["message"], ref=m["ref"]
        )
        for m in prepared
    ]

    client = _client()
    try:
        response = client.sms.send(senderid=senderid.name, messages=prepared)
    except MoolreAPIError as exc:
        for r in records:
            r.status = SmsMessage.Status.FAILED
            r.raw_response = exc.raw_response
            r.save()
        raise

    now = timezone.now()
    for r in records:
        r.status = SmsMessage.Status.SENT
        r.sent_at = now
        r.raw_response = response
        r.save()
    return records


def check_sms_status(refs: list[str]) -> list[SmsMessage]:
    """Batch-check delivery status via `sms/status` (type=5).

    Source: docs.moolre.com/ai/sms-status.html -- the exact meaning of each
    integer status code isn't fully enumerated in the docs, so we just
    store it (`provider_status`) rather than guess at a mapping.
    """
    client = _client()
    response = client.sms.status(refs=refs)
    results = {item["ref"]: item["status"] for item in response.get("data") or []}

    updated = []
    for sms in SmsMessage.objects.filter(ref__in=refs):
        if sms.ref in results:
            sms.provider_status = results[sms.ref]
            sms.save(update_fields=["provider_status", "updated_at"])
        updated.append(sms)
    return updated


def get_sms_account_balance() -> int:
    """SMS credit balance via `sms/status` (type=2)."""
    client = _client()
    response = client.sms.account_status()
    return response["data"]["balance"]


def request_sender_id(name: str) -> SenderId:
    """Request a new Sender ID via `sms/query` (type=3)."""
    client = _client()
    client.sms.create_sender_id(senderids=[{"senderid": name}])
    sender_id, _ = SenderId.objects.get_or_create(
        name=name, defaults={"approval_status": SenderId.ApprovalStatus.PENDING}
    )
    return sender_id


def refresh_sender_id_status(sender_id: SenderId) -> SenderId:
    """Refresh one Sender ID's approval status via `sms/status` (type=1)."""
    client = _client()
    response = client.sms.sender_id_status(senderid=sender_id.name)
    data = response["data"]
    sender_id.approval_status = data.get("approval", sender_id.approval_status)
    sender_id.whitelisted = bool(data.get("whitelisted", sender_id.whitelisted))
    sender_id.save()
    return sender_id


def sync_sender_ids() -> list[SenderId]:
    """Pull the full list of Sender IDs via `sms/status` (type=7) and
    upsert local records.
    """
    client = _client()
    response = client.sms.list_sender_ids()
    records = []
    for item in response.get("data") or []:
        sender_id, _ = SenderId.objects.update_or_create(
            name=item["senderid"],
            defaults={
                "approval_status": item.get("approval", SenderId.ApprovalStatus.PENDING),
                "whitelisted": bool(item.get("whitelisted", False)),
                "moolre_id": str(item.get("id", "")),
            },
        )
        records.append(sender_id)
    return records


def approve_sender_id(sender_id: SenderId, *, approve: bool) -> SenderId:
    """Approve or reject a Sender ID via `sms/status` (type=6).

    Requires admin permission on Moolre's side (ASMQ09 if not authorized) --
    plan Section 8: "/approve/ ... IsAdminUser-only" at the API layer too.
    """
    client = _client()
    approve_code = 1 if approve else 2
    response = client.sms.approve_sender_ids(
        senderids=[{"senderid": sender_id.name, "approve": approve_code}]
    )
    data = (response.get("data") or [{}])[0]
    sender_id.approval_status = data.get(
        "approval", SenderId.ApprovalStatus.APPROVED if approve else SenderId.ApprovalStatus.REJECTED
    )
    sender_id.save()
    return sender_id


# -- WhatsApp ---------------------------------------------------------------------


def sync_whatsapp_templates() -> list[WhatsAppTemplate]:
    """Pull approved/pending/rejected templates via `whatsapp/template`."""
    client = _client()
    response = client.whatsapp.templates()
    records = []
    for item in response.get("data") or []:
        template, _ = WhatsAppTemplate.objects.update_or_create(
            template_id=item["id"],
            defaults={
                "name": item.get("name", ""),
                "language": item.get("language", "en"),
                "status": item.get("status", WhatsAppTemplate.Status.PENDING),
                "body": item.get("message", ""),
                "placeholders": item.get("placeholders", []),
            },
        )
        records.append(template)
    return records


def send_whatsapp_message(
    template: WhatsAppTemplate, *, recipient: str, ref: str | None = None, placeholders: dict | None = None
) -> WhatsAppMessage:
    """Send one templated WhatsApp message via `whatsapp/send`.

    `ref` is required here (even though Moolre treats it as optional) --
    without it, status can never be checked later (per the docs).
    """
    ref = ref or str(uuid.uuid4())
    msg = WhatsAppMessage.objects.create(
        template=template, recipient=recipient, ref=ref, placeholders=placeholders or {}
    )
    client = _client()
    response = client.whatsapp.send(
        template_name=template.name,
        language=template.language,
        messages=[{"recipient": recipient, "ref": ref, "placeholders": placeholders or {}}],
    )
    msg.raw_response = response
    msg.status = "accepted" if not response.get("error") else "rejected"
    msg.save()
    return msg


def check_whatsapp_status(refs: list[str]) -> list[WhatsAppMessage]:
    """Batch-check delivery status via `whatsapp/status`."""
    client = _client()
    response = client.whatsapp.status(refs=refs)
    results = {item["ref"]: item["status"] for item in response.get("data") or []}

    updated = []
    for msg in WhatsAppMessage.objects.filter(ref__in=refs):
        if msg.ref in results:
            msg.status = results[msg.ref]
            msg.save(update_fields=["status", "updated_at"])
        updated.append(msg)
    return updated
