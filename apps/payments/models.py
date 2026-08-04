"""
Payments (collections) domain models (plan Section 4).

Milestone 3 scope: PaymentRequest (USSD push) + WebhookEvent (audit log of
every inbound callback).
Milestone 4 scope: PaymentLink, VirtualAccount, PaymentIdTerminal.
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


class PaymentLink(models.Model):
    """A hosted Moolre Web POS payment link (plan Section 4).

    Source: docs.moolre.com/ai/generate-payment-link.html (POST /embed/link).
    """

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        EXPIRED = "expired", "Expired"

    wallet = models.ForeignKey(Wallet, on_delete=models.PROTECT, related_name="payment_links")
    externalref = models.CharField(max_length=64, unique=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=3, default="GHS")
    authorization_url = models.URLField(blank=True)
    reusable = models.BooleanField(default=False)
    expires_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    raw_response = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"PaymentLink({self.externalref})"


class VirtualAccount(models.Model):
    """A permanent virtual bank account for collections (plan Section 4).

    Source: docs.moolre.com/ai/create-bank-account-number.html --
    account/create, type=9. `uref` is the client-generated idempotency
    reference (docs call it "Unique request reference").
    """

    wallet = models.ForeignKey(Wallet, on_delete=models.PROTECT, related_name="virtual_accounts")
    accountno = models.CharField(max_length=32, blank=True)
    accountname = models.CharField(max_length=255, blank=True)
    bankname = models.CharField(max_length=255, blank=True)
    uref = models.CharField(max_length=64, unique=True)
    holder_first_name = models.CharField(max_length=100)
    holder_last_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    raw_response = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"VirtualAccount({self.accountno or self.uref})"


class PaymentIdTerminal(models.Model):
    """A reusable *203*paymentid# terminal (plan Section 4).

    Source: docs.moolre.com/ai/create-payment-id.html -- account/create,
    type=2.
    """

    wallet = models.ForeignKey(Wallet, on_delete=models.PROTECT, related_name="payment_id_terminals")
    paymentid = models.CharField(max_length=32, blank=True)
    holder_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20)
    externalref = models.CharField(max_length=64, blank=True)
    raw_response = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"PaymentIdTerminal({self.paymentid or self.holder_name})"
