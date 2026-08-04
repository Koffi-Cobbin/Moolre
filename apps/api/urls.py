from rest_framework.routers import DefaultRouter

from .views import (
    NameValidationViewSet,
    PaymentIdTerminalViewSet,
    PaymentLinkViewSet,
    PaymentRequestViewSet,
    SenderIdViewSet,
    SmsMessageViewSet,
    TransferViewSet,
    VirtualAccountViewSet,
    WalletViewSet,
    WhatsAppMessageViewSet,
    WhatsAppTemplateViewSet,
)

router = DefaultRouter()
router.register(r"wallets", WalletViewSet, basename="wallet")
router.register(r"payments/ussd", PaymentRequestViewSet, basename="payment-request")
router.register(r"payments/links", PaymentLinkViewSet, basename="payment-link")
router.register(r"payments/virtual-accounts", VirtualAccountViewSet, basename="virtual-account")
router.register(r"payments/payment-ids", PaymentIdTerminalViewSet, basename="payment-id-terminal")
router.register(r"transfers/validate-name", NameValidationViewSet, basename="validate-name")
router.register(r"transfers", TransferViewSet, basename="transfer")
router.register(r"sms/sender-ids", SenderIdViewSet, basename="sender-id")
router.register(r"sms", SmsMessageViewSet, basename="sms-message")
router.register(r"whatsapp/templates", WhatsAppTemplateViewSet, basename="whatsapp-template")
router.register(r"whatsapp/messages", WhatsAppMessageViewSet, basename="whatsapp-message")

urlpatterns = router.urls

# Reference-data routes (plan Section 8, "Reference / misc") are added
# here if that read-only slice is ever prioritized.
