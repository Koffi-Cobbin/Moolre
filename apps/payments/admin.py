from django.contrib import admin, messages

from . import services
from .models import PaymentIdTerminal, PaymentLink, PaymentRequest, VirtualAccount, WebhookEvent


@admin.register(PaymentRequest)
class PaymentRequestAdmin(admin.ModelAdmin):
    list_display = (
        "externalref",
        "wallet",
        "amount",
        "currency",
        "channel",
        "status",
        "otp_required",
        "created_at",
    )
    list_filter = ("status", "channel", "currency")
    search_fields = ("externalref", "transactionid", "payer_msisdn")
    readonly_fields = ("transactionid", "session_id", "raw_response", "created_at", "updated_at")
    actions = ["recheck_status"]

    @admin.action(description="Re-check status")
    def recheck_status(self, request, queryset):
        # Plan Section 9: "Re-check status" admin action.
        for payment_request in queryset:
            try:
                services.check_payment_status(payment_request)
            except Exception as exc:  # noqa: BLE001 -- surface any client error to the admin user
                self.message_user(
                    request, f"{payment_request}: failed to refresh ({exc})", level=messages.ERROR
                )
            else:
                self.message_user(request, f"{payment_request}: status refreshed")


@admin.register(WebhookEvent)
class WebhookEventAdmin(admin.ModelAdmin):
    list_display = ("id", "verified", "processed", "received_at")
    list_filter = ("verified", "processed")
    readonly_fields = ("raw_payload", "signature", "received_at")
    actions = ["resend_webhook_processing"]

    @admin.action(description="Resend webhook processing")
    def resend_webhook_processing(self, request, queryset):
        # Plan Section 9: "Resend webhook processing" (for debugging).
        from .models import PaymentRequest as PR

        for event in queryset:
            externalref = (event.raw_payload or {}).get("data", {}).get("externalref")
            payment_request = PR.objects.filter(externalref=externalref).first() if externalref else None
            if not payment_request:
                self.message_user(
                    request, f"Event {event.id}: no matching PaymentRequest ({externalref})", level=messages.ERROR
                )
                continue
            try:
                services.check_payment_status(payment_request)
            except Exception as exc:  # noqa: BLE001
                self.message_user(request, f"Event {event.id}: failed ({exc})", level=messages.ERROR)
            else:
                event.processed = True
                event.save(update_fields=["processed"])
                self.message_user(request, f"Event {event.id}: reprocessed")


@admin.register(PaymentLink)
class PaymentLinkAdmin(admin.ModelAdmin):
    list_display = ("externalref", "wallet", "amount", "currency", "reusable", "status", "created_at")
    list_filter = ("status", "reusable", "currency")
    search_fields = ("externalref", "authorization_url")
    readonly_fields = ("authorization_url", "raw_response", "created_at", "updated_at")


@admin.register(VirtualAccount)
class VirtualAccountAdmin(admin.ModelAdmin):
    list_display = ("accountno", "accountname", "bankname", "wallet", "phone", "created_at")
    search_fields = ("accountno", "accountname", "uref", "phone", "email")
    readonly_fields = ("accountno", "accountname", "bankname", "raw_response", "created_at", "updated_at")


@admin.register(PaymentIdTerminal)
class PaymentIdTerminalAdmin(admin.ModelAdmin):
    list_display = ("paymentid", "holder_name", "phone", "wallet", "created_at")
    search_fields = ("paymentid", "holder_name", "phone", "externalref")
    readonly_fields = ("paymentid", "raw_response", "created_at", "updated_at")
