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
