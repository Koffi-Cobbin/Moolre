from django.contrib import admin
from django.contrib import messages

from . import services
from .models import SettlementConfig, Wallet


class SettlementConfigInline(admin.StackedInline):
    model = SettlementConfig
    extra = 0


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = (
        "accountname",
        "accountnumber",
        "currency",
        "balance",
        "api_enabled",
        "last_synced_at",
    )
    list_filter = ("currency", "api_enabled")
    search_fields = ("accountname", "accountnumber", "paymentid")
    readonly_fields = ("secret", "last_synced_at", "created_at", "updated_at")
    inlines = [SettlementConfigInline]
    actions = ["refresh_balance"]

    @admin.action(description="Refresh balance from Moolre")
    def refresh_balance(self, request, queryset):
        # Plan Section 9: "Re-check status" style admin action.
        for wallet in queryset:
            try:
                services.sync_balance(wallet)
            except Exception as exc:  # noqa: BLE001 — surface any client error to the admin user
                self.message_user(
                    request, f"{wallet}: failed to refresh ({exc})", level=messages.ERROR
                )
            else:
                self.message_user(request, f"{wallet}: balance refreshed")
