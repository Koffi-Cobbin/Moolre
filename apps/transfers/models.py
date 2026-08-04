"""
Transfers (disbursements) domain models (plan Section 4 + Section 8).

Plan Section 8 ("AuthN/Z tiers"): "Transfers/disbursements -- highest tier:
separate permission class, optional maker-checker/approval step before the
transfer is actually sent to Moolre, and full audit logging of who
triggered it." Transfer.status therefore includes a PENDING_APPROVAL state
that exists purely locally -- Moolre is never called until someone with
approval rights calls services.approve_and_send_transfer().
"""

from django.conf import settings
from django.db import models

from apps.wallets.models import Wallet


class NameValidationLog(models.Model):
    """Audit log of every name-validation check (plan Section 4).

    Source: docs.moolre.com/ai/validate-name.html.
    """

    class Status(models.TextChoices):
        FOUND = "found", "Found"
        NOT_FOUND = "not_found", "Not Found"

    receiver = models.CharField(max_length=32)
    channel = models.CharField(max_length=8, help_text="1=MTN, 6=Telecel, 7=AT, 2=Instant Bank Transfer")
    resolved_name = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices)
    raw_response = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"NameValidationLog({self.receiver}, {self.status})"


class Transfer(models.Model):
    """A disbursement -- either an external payout (MoMo/bank) or an
    internal wallet-to-wallet transfer (plan Section 4).

    `externalref` is generated client-side before any Moolre call and
    reused on every retry (plan Section 11).
    """

    class Kind(models.TextChoices):
        EXTERNAL = "external", "External (MoMo/Bank)"
        INTERNAL = "internal", "Internal (wallet-to-wallet)"

    class Status(models.TextChoices):
        PENDING_APPROVAL = "pending_approval", "Pending Approval"
        REJECTED = "rejected", "Rejected"
        OTP_PENDING = "otp_pending", "Awaiting OTP"
        PROCESSING = "processing", "Processing"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"

    wallet = models.ForeignKey(Wallet, on_delete=models.PROTECT, related_name="transfers")
    kind = models.CharField(max_length=10, choices=Kind.choices, default=Kind.EXTERNAL)
    channel = models.CharField(max_length=8, blank=True, help_text="Required for external transfers")
    currency = models.CharField(max_length=3, default="GHS")
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    receiver = models.CharField(max_length=64)
    sublistid = models.CharField(max_length=32, blank=True)

    externalref = models.CharField(max_length=64, unique=True)
    reference = models.CharField(max_length=255, blank=True)
    transactionid = models.CharField(max_length=64, blank=True)
    thirdpartyref = models.CharField(max_length=64, blank=True)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING_APPROVAL)
    fee = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    network_fee = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Maker-checker (plan Section 8) -- Moolre is never called until this
    # is populated via services.approve_and_send_transfer().
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="requested_transfers", null=True, blank=True,
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="approved_transfers", null=True, blank=True,
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    raw_response = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.externalref} ({self.get_status_display()})"
