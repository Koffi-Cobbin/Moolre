"""
Payments (collections) domain models (plan Section 4).

Milestone 3 scope: PaymentRequest (USSD push) + WebhookEvent (audit log of
every inbound callback). PaymentLink, VirtualAccount, and PaymentIdTerminal
remain Milestone 4 -- see the TODO at the bottom of this file.
"""

from django.db import models

from apps.wallets.models import Wallet


class PaymentRequest(models.Model):
    """A USSD push collection request (plan Section 4).

    `externalref` is generated client-side *before* calling Moolre and
    reused on every retry -- never regenerated (plan Section 11).
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        OTP_PENDING = "otp_pending", "Awaiting OTP"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"

    wallet = models.ForeignKey(
        Wallet, on_delete=models.PROTECT, related_name="payment_requests"
    )
    channel = models.IntegerField(help_text="Moolre MoMo network code (e.g. 13=MTN, 6=Telecel, 7=AT)")
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=3, default="GHS")
    payer_msisdn = models.CharField(max_length=20)

    externalref = models.CharField(max_length=64, unique=True)
    transactionid = models.CharField(max_length=64, blank=True)
    session_id = models.CharField(max_length=64, blank=True)

    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING
    )
    otp_required = models.BooleanField(default=False)

    raw_response = models.JSONField(
        null=True, blank=True, help_text="Last raw API payload, for debugging"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.externalref} ({self.get_status_display()})"


class WebhookEvent(models.Model):
    """Append-only audit log of every inbound Moolre callback (plan Section 4/6).

    Stored *before* any processing happens, so a crash mid-handler is still
    recoverable/replayable. Moolre's payment webhook has no documented
    signature header (docs.moolre.com/ai/payment-webhook.md), so `verified`
    reflects the "verify, don't trust" status-check round-trip (plan
    Section 6 / moolre_client.signing), not an HMAC check.
    """

    raw_payload = models.JSONField()
    signature = models.CharField(max_length=255, blank=True)
    verified = models.BooleanField(default=False)
    processed = models.BooleanField(default=False)
    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-received_at"]

    def __str__(self):
        externalref = (self.raw_payload or {}).get("data", {}).get("externalref", "?")
        return f"WebhookEvent({externalref}, processed={self.processed})"


# TODO(milestone-4): PaymentLink, VirtualAccount, PaymentIdTerminal
# (plan Section 4, remaining "payments (collections)" models).
