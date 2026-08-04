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


# ---------------------------------------------------------------------------
# Payment links / virtual accounts / payment IDs -- Milestone 4 scope
# (plan Section 8, "Collections" table)
# ---------------------------------------------------------------------------

from apps.payments.models import PaymentIdTerminal, PaymentLink, VirtualAccount  # noqa: E402


class PaymentLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentLink
        fields = [
            "id",
            "wallet",
            "externalref",
            "amount",
            "currency",
            "authorization_url",
            "reusable",
            "expires_at",
            "metadata",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "authorization_url", "status", "created_at", "updated_at"]


class PaymentLinkCreateSerializer(serializers.Serializer):
    """Input shape for POST /api/payments/links/ (plan Section 8)."""

    wallet = serializers.PrimaryKeyRelatedField(queryset=Wallet.objects.all())
    amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    email = serializers.EmailField()
    externalref = serializers.CharField(required=False)
    reusable = serializers.BooleanField(required=False, default=False)
    callback = serializers.URLField(required=False)
    redirect = serializers.URLField(required=False)
    expiration_time = serializers.IntegerField(required=False)
    metadata = serializers.DictField(required=False)


class VirtualAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = VirtualAccount
        fields = [
            "id",
            "wallet",
            "accountno",
            "accountname",
            "bankname",
            "uref",
            "holder_first_name",
            "holder_last_name",
            "phone",
            "email",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "accountno", "accountname", "bankname", "created_at", "updated_at"]


class VirtualAccountCreateSerializer(serializers.Serializer):
    """Input shape for POST /api/payments/virtual-accounts/ (plan Section 8)."""

    wallet = serializers.PrimaryKeyRelatedField(queryset=Wallet.objects.all())
    firstname = serializers.CharField()
    lastname = serializers.CharField()
    phone = serializers.CharField()
    email = serializers.EmailField()
    uref = serializers.CharField(required=False)
    amount = serializers.DecimalField(max_digits=14, decimal_places=2, required=False)


class PaymentIdTerminalSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentIdTerminal
        fields = [
            "id",
            "wallet",
            "paymentid",
            "holder_name",
            "phone",
            "externalref",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "paymentid", "created_at", "updated_at"]


class PaymentIdTerminalCreateSerializer(serializers.Serializer):
    """Input shape for POST /api/payments/payment-ids/ (plan Section 8)."""

    wallet = serializers.PrimaryKeyRelatedField(queryset=Wallet.objects.all())
    phone = serializers.CharField()
    name = serializers.CharField()
    externalref = serializers.CharField(required=False)


# ---------------------------------------------------------------------------
# Transfers (disbursements) -- Milestone 5 scope (plan Section 8, "Disbursements")
# ---------------------------------------------------------------------------

from apps.transfers.models import NameValidationLog, Transfer  # noqa: E402


class NameValidationLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = NameValidationLog
        fields = ["id", "receiver", "channel", "resolved_name", "status", "created_at"]
        read_only_fields = fields


class ValidateNameSerializer(serializers.Serializer):
    """Input shape for POST /api/transfers/validate-name/."""

    wallet = serializers.PrimaryKeyRelatedField(queryset=Wallet.objects.all())
    receiver = serializers.CharField()
    channel = serializers.CharField()
    sublistid = serializers.CharField(required=False)


class TransferSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transfer
        fields = [
            "id",
            "wallet",
            "kind",
            "channel",
            "currency",
            "amount",
            "receiver",
            "sublistid",
            "externalref",
            "reference",
            "transactionid",
            "thirdpartyref",
            "status",
            "fee",
            "network_fee",
            "requested_by",
            "approved_by",
            "approved_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id", "kind", "transactionid", "thirdpartyref", "status", "fee",
            "network_fee", "requested_by", "approved_by", "approved_at",
            "created_at", "updated_at",
        ]


class TransferCreateSerializer(serializers.Serializer):
    """Input shape for POST /api/transfers/ (external MoMo/bank payout).

    Only writes a PENDING_APPROVAL record -- plan Section 8: "gated by
    permission/approval" -- see PATCH .../approve/.
    """

    wallet = serializers.PrimaryKeyRelatedField(queryset=Wallet.objects.all())
    channel = serializers.CharField()
    amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    receiver = serializers.CharField()
    externalref = serializers.CharField(required=False)
    sublistid = serializers.CharField(required=False)
    reference = serializers.CharField(required=False)


class InternalTransferCreateSerializer(serializers.Serializer):
    """Input shape for POST /api/transfers/internal/."""

    wallet = serializers.PrimaryKeyRelatedField(queryset=Wallet.objects.all())
    amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    receiver = serializers.CharField()
    externalref = serializers.CharField(required=False)
    reference = serializers.CharField(required=False)


class ConfirmTransferOtpSerializer(serializers.Serializer):
    """Input shape for POST /api/transfers/{externalref}/confirm-otp/."""

    otpcode = serializers.CharField()


# ---------------------------------------------------------------------------
# Messaging: SMS + WhatsApp -- Milestone 6 scope (plan Section 8)
# ---------------------------------------------------------------------------

from apps.messaging.models import SenderId, SmsMessage, WhatsAppMessage, WhatsAppTemplate  # noqa: E402


class SenderIdSerializer(serializers.ModelSerializer):
    class Meta:
        model = SenderId
        fields = ["id", "name", "approval_status", "whitelisted", "moolre_id", "created_at", "updated_at"]
        read_only_fields = ["id", "approval_status", "whitelisted", "moolre_id", "created_at", "updated_at"]


class SenderIdCreateSerializer(serializers.Serializer):
    """Input shape for POST /api/sms/sender-ids/."""

    name = serializers.CharField(max_length=11)


class SmsMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = SmsMessage
        fields = [
            "id", "senderid", "recipient", "message", "ref", "status",
            "provider_status", "sent_at", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "status", "provider_status", "sent_at", "created_at", "updated_at"]


class SmsMessageCreateSerializer(serializers.Serializer):
    """Input shape for POST /api/sms/ (plan Section 8: accepts an array of
    recipients for bulk sends).
    """

    senderid = serializers.PrimaryKeyRelatedField(queryset=SenderId.objects.all())
    recipient = serializers.CharField(required=False)
    message = serializers.CharField(required=False)
    messages = serializers.ListField(child=serializers.DictField(), required=False)

    def validate(self, attrs):
        has_single = "recipient" in attrs and "message" in attrs
        has_bulk = "messages" in attrs
        if not (has_single or has_bulk):
            raise serializers.ValidationError(
                "Provide either recipient+message (single) or messages (bulk array)."
            )
        return attrs


class WhatsAppTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = WhatsAppTemplate
        fields = ["id", "template_id", "name", "language", "status", "body", "placeholders", "updated_at"]
        read_only_fields = fields


class WhatsAppMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = WhatsAppMessage
        fields = ["id", "template", "recipient", "ref", "placeholders", "status", "created_at", "updated_at"]
        read_only_fields = ["id", "status", "created_at", "updated_at"]


class WhatsAppMessageCreateSerializer(serializers.Serializer):
    """Input shape for POST /api/whatsapp/messages/."""

    template = serializers.PrimaryKeyRelatedField(queryset=WhatsAppTemplate.objects.all())
    recipient = serializers.CharField()
    ref = serializers.CharField(required=False)
    placeholders = serializers.DictField(required=False)


class RefListSerializer(serializers.Serializer):
    """Input shape for POST /api/whatsapp/messages/status/bulk/."""

    refs = serializers.ListField(child=serializers.CharField())
