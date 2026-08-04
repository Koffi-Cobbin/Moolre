"""
Messaging (SMS + WhatsApp) domain models (plan Section 4).

Not tied to a Wallet FK -- Moolre's messaging credentials (X-API-VASKEY)
are account-level, not per-wallet, matching how the plan's own model list
for this domain has no `wallet` field (unlike payments/transfers).
"""

from django.db import models


class SenderId(models.Model):
    """A registered SMS Sender ID (plan Section 4).

    Source: docs.moolre.com/ai/{create,sender-id-status,list,approve}-
    sender-id.html. Moolre's own `approval` values are "Pending" /
    "Approved" / "Rejected" -- mirrored here as text choices.
    """

    class ApprovalStatus(models.TextChoices):
        PENDING = "Pending", "Pending"
        APPROVED = "Approved", "Approved"
        REJECTED = "Rejected", "Rejected"

    name = models.CharField(max_length=11, unique=True, help_text="Max 11 characters per Moolre's limit")
    approval_status = models.CharField(
        max_length=16, choices=ApprovalStatus.choices, default=ApprovalStatus.PENDING
    )
    whitelisted = models.BooleanField(default=False)
    moolre_id = models.CharField(max_length=32, blank=True, help_text="Moolre's internal sender ID record id")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.approval_status})"


class SmsMessage(models.Model):
    """A single SMS send, tracked by its client-generated `ref` (plan Section 4).

    Source: docs.moolre.com/ai/{send-sms,sms-status}.html. Moolre's
    `sms/status` (type=5) returns a raw integer `status` per ref whose
    exact meaning isn't fully enumerated in the docs beyond examples (2, 3
    were observed) -- stored as-is in `provider_status` alongside a best-
    effort normalized `status`.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"

    senderid = models.ForeignKey(SenderId, on_delete=models.PROTECT, related_name="messages")
    recipient = models.CharField(max_length=20)
    message = models.TextField()
    ref = models.CharField(max_length=64, unique=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    provider_status = models.IntegerField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    raw_response = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"SmsMessage({self.ref}, {self.status})"


class WhatsAppTemplate(models.Model):
    """A cached copy of an approved/pending/rejected WhatsApp template
    (plan Section 4).

    Source: docs.moolre.com/ai/whatsapp-get-templates.html.
    """

    class Status(models.TextChoices):
        APPROVED = "APPROVED", "Approved"
        PENDING = "PENDING", "Pending"
        REJECTED = "REJECTED", "Rejected"

    template_id = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=255)
    language = models.CharField(max_length=8, default="en")
    status = models.CharField(max_length=16, choices=Status.choices)
    body = models.TextField(blank=True)
    placeholders = models.JSONField(default=list, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.language}, {self.status})"


class WhatsAppMessage(models.Model):
    """A single WhatsApp templated send, tracked by its client-generated
    `ref` (plan Section 4).

    Source: docs.moolre.com/ai/{whatsapp-send-message,
    whatsapp-message-status}.html. Without a `ref`, Moolre cannot report
    status later -- so `ref` is required here even though Moolre's own API
    treats it as optional.
    """

    template = models.ForeignKey(WhatsAppTemplate, on_delete=models.PROTECT, related_name="messages")
    recipient = models.CharField(max_length=20)
    ref = models.CharField(max_length=64, unique=True)
    placeholders = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=16, blank=True, help_text="Raw Moolre status string, e.g. accepted/read")
    raw_response = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"WhatsAppMessage({self.ref}, {self.status or 'unknown'})"
