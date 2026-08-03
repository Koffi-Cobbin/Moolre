from django.db import models
from django_cryptography.fields import encrypt


class Wallet(models.Model):
    """A Moolre business wallet/account (plan Section 4).

    `accountnumber` is Moolre's identifier for the wallet and is what every
    other domain (payments, transfers) references via FK/lookup.
    """

    accountnumber = models.CharField(max_length=32, unique=True)
    accountname = models.CharField(max_length=255)
    currency = models.CharField(max_length=3, default="GHS")
    paymentid = models.CharField(
        max_length=32, blank=True, help_text="Reusable *203*id# payment ID"
    )
    api_enabled = models.BooleanField(default=False)
    callback_url = models.URLField(blank=True)

    # Returned once on account/create — encrypted at rest (plan Section 10).
    secret = encrypt(models.CharField(max_length=255, blank=True))

    balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    last_synced_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.accountname} ({self.accountnumber})"


class SettlementConfig(models.Model):
    """Settlement configuration attached to a wallet (plan Section 4).

    Mirrors the `settlement` object accepted by `account/create` and
    `account/update` (fields: frequency, channel, recipient, sublist —
    see docs.moolre.com/ai/update-account.md).
    """

    wallet = models.OneToOneField(
        Wallet, on_delete=models.CASCADE, related_name="settlement"
    )
    frequency = models.CharField(max_length=32, blank=True)
    channel = models.CharField(max_length=32, blank=True)
    recipient = models.CharField(max_length=64, blank=True)
    sublist = models.CharField(max_length=64, blank=True)

    def __str__(self):
        return f"Settlement for {self.wallet.accountnumber}"
