from rest_framework.routers import DefaultRouter

from .views import WalletViewSet

router = DefaultRouter()
router.register(r"wallets", WalletViewSet, basename="wallet")

urlpatterns = router.urls

# Payments / transfers / messaging / reference-data routes (plan Section 8)
# are added here as their services.py modules land in later milestones.
