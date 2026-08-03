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

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.moolre_client.exceptions import MoolreAPIError, MoolreError, MoolreValidationError
from apps.wallets import services
from apps.wallets.models import Wallet

from .serializers import WalletCreateSerializer, WalletSerializer, WalletUpdateSerializer


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
