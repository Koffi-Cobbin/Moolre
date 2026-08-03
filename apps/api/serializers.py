"""
Serializers for the internal REST API (plan Section 8).

Only the Wallets slice is implemented in Milestone 1 — payments, transfers,
messaging, and reference-data serializers land alongside their respective
services in Milestones 3-7.
"""

from rest_framework import serializers

from apps.wallets.models import SettlementConfig, Wallet


class SettlementConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = SettlementConfig
        fields = ["frequency", "channel", "recipient", "sublist"]


class WalletSerializer(serializers.ModelSerializer):
    settlement = SettlementConfigSerializer(read_only=True)

    class Meta:
        model = Wallet
        fields = [
            "id",
            "accountnumber",
            "accountname",
            "currency",
            "paymentid",
            "api_enabled",
            "callback_url",
            "balance",
            "last_synced_at",
            "settlement",
            "created_at",
            "updated_at",
        ]
        # secret is intentionally excluded — never serialize it back to a
        # frontend/consumer (plan Section 10: encrypted at rest).
        read_only_fields = [
            "id",
            "paymentid",
            "balance",
            "last_synced_at",
            "created_at",
            "updated_at",
        ]


class WalletCreateSerializer(serializers.Serializer):
    """Input shape for POST /api/wallets/ (plan Section 8)."""

    accountname = serializers.CharField()
    currency = serializers.CharField(required=False)
    callback_url = serializers.URLField()
    api_enabled = serializers.BooleanField(required=False, default=False)
    settlement = serializers.DictField(required=False)


class WalletUpdateSerializer(serializers.Serializer):
    """Input shape for PATCH /api/wallets/{id}/ (plan Section 8)."""

    accountname = serializers.CharField(required=False)
    api_enabled = serializers.BooleanField(required=False)
    callback_url = serializers.URLField(required=False)
    settlement = serializers.DictField(required=False)


# ---------------------------------------------------------------------------
# Payments (collections) -- Milestone 3 scope (plan Section 8, "Collections")
# ---------------------------------------------------------------------------

from apps.payments.models import PaymentRequest  # noqa: E402


class PaymentRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentRequest
        fields = [
            "id",
            "wallet",
            "channel",
            "amount",
            "currency",
            "payer_msisdn",
            "externalref",
            "transactionid",
            "session_id",
            "status",
            "otp_required",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "transactionid",
            "session_id",
            "status",
            "otp_required",
            "created_at",
            "updated_at",
        ]


class PaymentRequestCreateSerializer(serializers.Serializer):
    """Input shape for POST /api/payments/ussd/ (plan Section 8)."""

    wallet = serializers.PrimaryKeyRelatedField(queryset=Wallet.objects.all())
    channel = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    payer_msisdn = serializers.CharField()
    externalref = serializers.CharField(required=False)
    reference = serializers.CharField(required=False)


class ConfirmOtpSerializer(serializers.Serializer):
    """Input shape for POST /api/payments/ussd/{externalref}/confirm-otp/."""

    otpcode = serializers.CharField()
