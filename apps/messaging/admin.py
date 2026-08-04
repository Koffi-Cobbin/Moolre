from django.contrib import admin, messages

from . import services
from .models import SenderId, SmsMessage, WhatsAppMessage, WhatsAppTemplate


@admin.register(SenderId)
class SenderIdAdmin(admin.ModelAdmin):
    list_display = ("name", "approval_status", "whitelisted", "updated_at")
    list_filter = ("approval_status", "whitelisted")
    search_fields = ("name",)
    actions = ["refresh_status", "approve", "reject"]

    @admin.action(description="Refresh approval status from Moolre")
    def refresh_status(self, request, queryset):
        for sender_id in queryset:
            try:
                services.refresh_sender_id_status(sender_id)
            except Exception as exc:  # noqa: BLE001
                self.message_user(request, f"{sender_id}: failed ({exc})", level=messages.ERROR)
            else:
                self.message_user(request, f"{sender_id}: refreshed")

    @admin.action(description="Approve")
    def approve(self, request, queryset):
        for sender_id in queryset:
            try:
                services.approve_sender_id(sender_id, approve=True)
            except Exception as exc:  # noqa: BLE001
                self.message_user(request, f"{sender_id}: failed ({exc})", level=messages.ERROR)
            else:
                self.message_user(request, f"{sender_id}: approved")

    @admin.action(description="Reject")
    def reject(self, request, queryset):
        for sender_id in queryset:
            try:
                services.approve_sender_id(sender_id, approve=False)
            except Exception as exc:  # noqa: BLE001
                self.message_user(request, f"{sender_id}: failed ({exc})", level=messages.ERROR)
            else:
                self.message_user(request, f"{sender_id}: rejected")


@admin.register(SmsMessage)
class SmsMessageAdmin(admin.ModelAdmin):
    list_display = ("ref", "senderid", "recipient", "status", "provider_status", "created_at")
    list_filter = ("status", "senderid")
    search_fields = ("ref", "recipient")
    readonly_fields = ("raw_response", "sent_at", "created_at", "updated_at")
    actions = ["recheck_status"]

    @admin.action(description="Re-check delivery status")
    def recheck_status(self, request, queryset):
        refs = list(queryset.values_list("ref", flat=True))
        try:
            services.check_sms_status(refs)
        except Exception as exc:  # noqa: BLE001
            self.message_user(request, f"Failed to refresh: {exc}", level=messages.ERROR)
        else:
            self.message_user(request, f"Refreshed status for {len(refs)} message(s)")


@admin.register(WhatsAppTemplate)
class WhatsAppTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "language", "status", "template_id", "updated_at")
    list_filter = ("status", "language")
    search_fields = ("name", "template_id")
    actions = ["sync_from_moolre"]

    @admin.action(description="Sync templates from Moolre")
    def sync_from_moolre(self, request, queryset):
        try:
            records = services.sync_whatsapp_templates()
        except Exception as exc:  # noqa: BLE001
            self.message_user(request, f"Failed to sync: {exc}", level=messages.ERROR)
        else:
            self.message_user(request, f"Synced {len(records)} template(s)")


@admin.register(WhatsAppMessage)
class WhatsAppMessageAdmin(admin.ModelAdmin):
    list_display = ("ref", "template", "recipient", "status", "created_at")
    list_filter = ("status", "template")
    search_fields = ("ref", "recipient")
    readonly_fields = ("raw_response", "created_at", "updated_at")
    actions = ["recheck_status"]

    @admin.action(description="Re-check delivery status")
    def recheck_status(self, request, queryset):
        refs = list(queryset.values_list("ref", flat=True))
        try:
            services.check_whatsapp_status(refs)
        except Exception as exc:  # noqa: BLE001
            self.message_user(request, f"Failed to refresh: {exc}", level=messages.ERROR)
        else:
            self.message_user(request, f"Refreshed status for {len(refs)} message(s)")
