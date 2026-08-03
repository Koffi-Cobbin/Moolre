from rest_framework.routers import DefaultRouter

from .views import PaymentRequestViewSet, WalletViewSet

router = DefaultRouter()
router.register(r"wallets", WalletViewSet, basename="wallet")
router.register(r"payments/ussd", PaymentRequestViewSet, basename="payment-request")

urlpatterns = router.urls

# Transfers / messaging / reference-data routes (plan Section 8) are added
# here as their services.py modules land in later milestones.
