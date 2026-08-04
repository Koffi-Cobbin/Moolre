"""
Wallets API views (plan Section 8, "Wallets" table).

Only this slice is implemented in Milestone 1 (build order, plan Section 13:
"Scaffolding ... admin skeleton" then "Wallets: create/update/status/
list-transactions, admin views"). Payments/transfers/messaging/reference
views land with their respective milestones.

Every response is normalized into the envelope described in plan Section 8
("Cross-cutting API concerns"): {"success": bool, "code": str,
"message": str, "data": {...}} — so consumers never parse Moolre-specific
codes directly.
"""

from __future__ import annotations

import uuid

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from apps.moolre_client.exceptions import MoolreAPIError, MoolreError, MoolreValidationError
from apps.wallets import services
from apps.wallets.models import Wallet

from apps.payments import services as payment_services
from apps.payments.models import PaymentIdTerminal, PaymentLink, PaymentRequest, VirtualAccount

from apps.transfers import services as transfer_services
from apps.transfers.models import Transfer

from .serializers import (
    ConfirmOtpSerializer,
    ConfirmTransferOtpSerializer,
    InternalTransferCreateSerializer,
    NameValidationLogSerializer,
    PaymentIdTerminalCreateSerializer,
    PaymentIdTerminalSerializer,
    PaymentLinkCreateSerializer,
    PaymentLinkSerializer,
    PaymentRequestCreateSerializer,
    PaymentRequestSerializer,
    TransferCreateSerializer,
    TransferSerializer,
    ValidateNameSerializer,
    VirtualAccountCreateSerializer,
    VirtualAccountSerializer,
    WalletCreateSerializer,
    WalletSerializer,
    WalletUpdateSerializer,
)


def envelope(*, success: bool, data=None, code: str | None = None, message: str = "") -> dict:
    return {"success": success, "code": code, "message": message, "data": data}


class WalletViewSet(viewsets.ModelViewSet):
    """
    /api/wallets/                        GET  list, POST create
    /api/wallets/{id}/                   GET  retrieve, PATCH update
    /api/wallets/{id}/balance/            GET  refresh + return balance
    /api/wallets/{id}/transactions/       GET  list transactions (filters)
    """

    queryset = Wallet.objects.all()
    serializer_class = WalletSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response(envelope(success=True, data=serializer.data))

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(envelope(success=True, data=serializer.data))

    def create(self, request, *args, **kwargs):
        payload = WalletCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        try:
            wallet = services.create_wallet(**payload.validated_data)
        except MoolreError as exc:
            return _error_response(exc)
        return Response(
            envelope(success=True, data=WalletSerializer(wallet).data),
            status=status.HTTP_201_CREATED,
        )

    def partial_update(self, request, *args, **kwargs):
        wallet = self.get_object()
        payload = WalletUpdateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        try:
            wallet = services.update_wallet(wallet, **payload.validated_data)
        except MoolreError as exc:
            return _error_response(exc)
        return Response(envelope(success=True, data=WalletSerializer(wallet).data))

    @action(detail=True, methods=["get"])
    def balance(self, request, pk=None):
        wallet = self.get_object()
        try:
            wallet = services.sync_balance(wallet)
        except MoolreError as exc:
            return _error_response(exc)
        return Response(
            envelope(success=True, data={"balance": str(wallet.balance)})
        )

    @action(detail=True, methods=["get"])
    def transactions(self, request, pk=None):
        wallet = self.get_object()
        try:
            txns = services.list_transactions(
                wallet,
                startdate=request.query_params.get("start"),
                enddate=request.query_params.get("end"),
                limit=request.query_params.get("limit"),
                status=request.query_params.get("status"),
            )
        except MoolreError as exc:
            return _error_response(exc)
        return Response(envelope(success=True, data={"transactions": txns}))


def _error_response(exc: MoolreError) -> Response:
    code = getattr(exc, "code", None)
    http_status = (
        status.HTTP_400_BAD_REQUEST
        if isinstance(exc, (MoolreValidationError, MoolreAPIError))
        else status.HTTP_502_BAD_GATEWAY
    )
    return Response(
        envelope(success=False, code=code, message=str(exc)), status=http_status
    )


class PaymentRequestViewSet(viewsets.ModelViewSet):
    """
    /api/payments/ussd/                              GET list, POST create
    /api/payments/ussd/{externalref}/                GET retrieve
    /api/payments/ussd/{externalref}/confirm-otp/    POST resubmit with otpcode
    /api/payments/ussd/{externalref}/status/          GET on-demand status refresh

    Mirrors plan Section 8's "Collections" table -- the {externalref}/status/
    route lives here (mounted at /api/payments/ussd/.../status/) rather than
    the separate top-level /api/payments/{externalref}/status/ path, since
    payment links/virtual accounts (Milestone 4) will need their own status
    lookups too and DRF routers don't share a lookup field across viewsets.
    """

    queryset = PaymentRequest.objects.all()
    serializer_class = PaymentRequestSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]
    lookup_field = "externalref"
    lookup_value_regex = "[^/]+"

    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response(envelope(success=True, data=serializer.data))

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(envelope(success=True, data=serializer.data))

    def create(self, request, *args, **kwargs):
        payload = PaymentRequestCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = dict(payload.validated_data)
        wallet = data.pop("wallet")
        # Idempotency-Key handling (plan Section 8): generate an externalref
        # if the caller didn't supply one, so a client can safely retry.
        data.setdefault("externalref", request.headers.get("Idempotency-Key") or str(uuid.uuid4()))
        try:
            payment_request = payment_services.initiate_ussd_payment(wallet, **data)
        except MoolreError as exc:
            return _error_response(exc)
        return Response(
            envelope(success=True, data=PaymentRequestSerializer(payment_request).data),
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="confirm-otp")
    def confirm_otp(self, request, externalref=None):
        payment_request = self.get_object()
        payload = ConfirmOtpSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        try:
            payment_request = payment_services.confirm_otp(
                payment_request, otpcode=payload.validated_data["otpcode"]
            )
        except MoolreError as exc:
            return _error_response(exc)
        return Response(envelope(success=True, data=PaymentRequestSerializer(payment_request).data))

    @action(detail=True, methods=["get"], url_path="status")
    def status_check(self, request, externalref=None):
        payment_request = self.get_object()
        try:
            payment_request = payment_services.check_payment_status(payment_request)
        except MoolreError as exc:
            return _error_response(exc)
        return Response(envelope(success=True, data=PaymentRequestSerializer(payment_request).data))


class PaymentLinkViewSet(viewsets.ModelViewSet):
    """
    /api/payments/links/                GET list, POST create (embed/link)
    /api/payments/links/{externalref}/  GET retrieve
    """

    queryset = PaymentLink.objects.all()
    serializer_class = PaymentLinkSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]
    lookup_field = "externalref"
    lookup_value_regex = "[^/]+"

    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response(envelope(success=True, data=serializer.data))

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(envelope(success=True, data=serializer.data))

    def create(self, request, *args, **kwargs):
        payload = PaymentLinkCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = dict(payload.validated_data)
        wallet = data.pop("wallet")
        data.setdefault("externalref", request.headers.get("Idempotency-Key") or str(uuid.uuid4()))
        try:
            payment_link = payment_services.create_payment_link(wallet, **data)
        except MoolreError as exc:
            return _error_response(exc)
        return Response(
            envelope(success=True, data=PaymentLinkSerializer(payment_link).data),
            status=status.HTTP_201_CREATED,
        )


class VirtualAccountViewSet(viewsets.ModelViewSet):
    """
    /api/payments/virtual-accounts/  GET list, POST create (account/create type=9)
    """

    queryset = VirtualAccount.objects.all()
    serializer_class = VirtualAccountSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]

    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response(envelope(success=True, data=serializer.data))

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(envelope(success=True, data=serializer.data))

    def create(self, request, *args, **kwargs):
        payload = VirtualAccountCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = dict(payload.validated_data)
        wallet = data.pop("wallet")
        data.setdefault("uref", request.headers.get("Idempotency-Key") or str(uuid.uuid4()))
        try:
            virtual_account = payment_services.create_virtual_account(wallet, **data)
        except MoolreError as exc:
            return _error_response(exc)
        return Response(
            envelope(success=True, data=VirtualAccountSerializer(virtual_account).data),
            status=status.HTTP_201_CREATED,
        )


class PaymentIdTerminalViewSet(viewsets.ModelViewSet):
    """
    /api/payments/payment-ids/  GET list, POST create (account/create type=2)
    """

    queryset = PaymentIdTerminal.objects.all()
    serializer_class = PaymentIdTerminalSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]

    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response(envelope(success=True, data=serializer.data))

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(envelope(success=True, data=serializer.data))

    def create(self, request, *args, **kwargs):
        payload = PaymentIdTerminalCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = dict(payload.validated_data)
        wallet = data.pop("wallet")
        data.setdefault("externalref", request.headers.get("Idempotency-Key") or str(uuid.uuid4()))
        try:
            terminal = payment_services.create_payment_id_terminal(wallet, **data)
        except MoolreError as exc:
            return _error_response(exc)
        return Response(
            envelope(success=True, data=PaymentIdTerminalSerializer(terminal).data),
            status=status.HTTP_201_CREATED,
        )


class TransferViewSet(viewsets.ModelViewSet):
    """
    /api/transfers/                       GET list, POST create (writes
                                           PENDING_APPROVAL only -- no
                                           Moolre call, plan Section 8)
    /api/transfers/internal/              POST create internal transfer
                                           (also PENDING_APPROVAL only)
    /api/transfers/{externalref}/         GET retrieve
    /api/transfers/{externalref}/approve/ POST approve + actually send
                                           (staff/admin only -- maker-checker)
    /api/transfers/{externalref}/reject/  POST reject without sending
    /api/transfers/{externalref}/confirm-otp/  POST resubmit with otpcode
    /api/transfers/{externalref}/status/  GET on-demand status refresh
    """

    queryset = Transfer.objects.all()
    serializer_class = TransferSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]
    lookup_field = "externalref"
    lookup_value_regex = "[^/]+"

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        for param in ("status", "channel"):
            value = request.query_params.get(param)
            if value:
                qs = qs.filter(**{param: value})
        serializer = self.get_serializer(qs, many=True)
        return Response(envelope(success=True, data=serializer.data))

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(envelope(success=True, data=serializer.data))

    def create(self, request, *args, **kwargs):
        """External MoMo/bank payout -- writes PENDING_APPROVAL only."""
        payload = TransferCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = dict(payload.validated_data)
        wallet = data.pop("wallet")
        data.setdefault("externalref", request.headers.get("Idempotency-Key") or str(uuid.uuid4()))
        xfer = transfer_services.create_transfer(wallet, requested_by=request.user, **data)
        return Response(
            envelope(success=True, data=TransferSerializer(xfer).data),
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["post"])
    def internal(self, request):
        """Internal wallet-to-wallet transfer -- writes PENDING_APPROVAL only."""
        payload = InternalTransferCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = dict(payload.validated_data)
        wallet = data.pop("wallet")
        data.setdefault("externalref", request.headers.get("Idempotency-Key") or str(uuid.uuid4()))
        xfer = transfer_services.create_internal_transfer(wallet, requested_by=request.user, **data)
        return Response(
            envelope(success=True, data=TransferSerializer(xfer).data),
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], permission_classes=[IsAdminUser])
    def approve(self, request, externalref=None):
        """The only route that actually sends money (plan Section 8:
        "separate permission class, optional maker-checker/approval step").
        Staff-only via IsAdminUser.
        """
        xfer = self.get_object()
        try:
            xfer = transfer_services.approve_and_send_transfer(xfer, approved_by=request.user)
        except (MoolreError, ValueError) as exc:
            return _error_response(exc) if isinstance(exc, MoolreError) else Response(
                envelope(success=False, message=str(exc)), status=status.HTTP_400_BAD_REQUEST
            )
        return Response(envelope(success=True, data=TransferSerializer(xfer).data))

    @action(detail=True, methods=["post"], permission_classes=[IsAdminUser])
    def reject(self, request, externalref=None):
        xfer = self.get_object()
        try:
            xfer = transfer_services.reject_transfer(xfer, rejected_by=request.user)
        except ValueError as exc:
            return Response(envelope(success=False, message=str(exc)), status=status.HTTP_400_BAD_REQUEST)
        return Response(envelope(success=True, data=TransferSerializer(xfer).data))

    @action(detail=True, methods=["post"], url_path="confirm-otp")
    def confirm_otp(self, request, externalref=None):
        xfer = self.get_object()
        payload = ConfirmTransferOtpSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        try:
            xfer = transfer_services.confirm_transfer_otp(xfer, otpcode=payload.validated_data["otpcode"])
        except MoolreError as exc:
            return _error_response(exc)
        return Response(envelope(success=True, data=TransferSerializer(xfer).data))

    @action(detail=True, methods=["get"], url_path="status")
    def status_check(self, request, externalref=None):
        xfer = self.get_object()
        try:
            xfer = transfer_services.check_transfer_status(xfer)
        except MoolreError as exc:
            return _error_response(exc)
        return Response(envelope(success=True, data=TransferSerializer(xfer).data))


class NameValidationViewSet(ViewSet):
    permission_classes = [IsAuthenticated]

    def create(self, request):
        payload = ValidateNameSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = dict(payload.validated_data)
        wallet = data.pop("wallet")
        try:
            log = transfer_services.validate_name(wallet, **data)
        except MoolreError as exc:
            return _error_response(exc)
        return Response(
            envelope(success=True, data=NameValidationLogSerializer(log).data),
            status=status.HTTP_201_CREATED,
        )
