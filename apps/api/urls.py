from rest_framework.routers import DefaultRouter

from .views import (
    NameValidationViewSet,
    PaymentIdTerminalViewSet,
    PaymentLinkViewSet,
    PaymentRequestViewSet,
    TransferViewSet,
    VirtualAccountViewSet,
    WalletViewSet,
)

router = DefaultRouter()
router.register(r"wallets", WalletViewSet, basename="wallet")
router.register(r"payments/ussd", PaymentRequestViewSet, basename="payment-request")
router.register(r"payments/links", PaymentLinkViewSet, basename="payment-link")
router.register(r"payments/virtual-accounts", VirtualAccountViewSet, basename="virtual-account")
router.register(r"payments/payment-ids", PaymentIdTerminalViewSet, basename="payment-id-terminal")
router.register(r"transfers/validate-name", NameValidationViewSet, basename="validate-name")
router.register(r"transfers", TransferViewSet, basename="transfer")

urlpatterns = router.urls

# Messaging / reference-data routes (plan Section 8) are added here as
# their services.py modules land in Milestone 6+.
