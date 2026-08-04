from django import forms
from django.contrib import admin, messages
from django.shortcuts import render

from . import services
from .models import NameValidationLog, Transfer


@admin.register(NameValidationLog)
class NameValidationLogAdmin(admin.ModelAdmin):
    list_display = ("receiver", "channel", "resolved_name", "status", "created_at")
    list_filter = ("status", "channel")
    search_fields = ("receiver", "resolved_name")
    readonly_fields = ("raw_response", "created_at")


class ConfirmRetryForm(forms.Form):
    confirm = forms.BooleanField(
        label="I understand this will move real money and cannot be undone.",
        required=True,
    )


@admin.register(Transfer)
class TransferAdmin(admin.ModelAdmin):
    list_display = (
        "externalref",
        "wallet",
        "kind",
        "amount",
        "currency",
        "receiver",
        "status",
        "requested_by",
        "approved_by",
        "created_at",
    )
    list_filter = ("status", "kind", "currency")
    search_fields = ("externalref", "transactionid", "receiver")
    readonly_fields = (
        "transactionid", "thirdpartyref", "fee", "network_fee",
        "raw_response", "approved_by", "approved_at", "created_at", "updated_at",
    )
    actions = ["approve_and_send", "recheck_status", "retry_transfer"]

    @admin.action(description="Approve and send (moves money)")
    def approve_and_send(self, request, queryset):
        # Plan Section 8: maker-checker -- this is the only admin action
        # that actually calls Moolre; it records `request.user` as approver.
        pending = queryset.filter(status=Transfer.Status.PENDING_APPROVAL)
        skipped = queryset.exclude(status=Transfer.Status.PENDING_APPROVAL).count()
        for xfer in pending:
            try:
                services.approve_and_send_transfer(xfer, approved_by=request.user)
            except Exception as exc:  # noqa: BLE001
                self.message_user(request, f"{xfer}: failed to send ({exc})", level=messages.ERROR)
            else:
                self.message_user(request, f"{xfer}: approved and sent by {request.user}")
        if skipped:
            self.message_user(
                request, f"{skipped} transfer(s) skipped -- not in PENDING_APPROVAL", level=messages.WARNING
            )

    @admin.action(description="Re-check status")
    def recheck_status(self, request, queryset):
        # Plan Section 9: "Re-check status" admin action.
        for xfer in queryset.exclude(status=Transfer.Status.PENDING_APPROVAL):
            try:
                services.check_transfer_status(xfer)
            except Exception as exc:  # noqa: BLE001
                self.message_user(request, f"{xfer}: failed to refresh ({exc})", level=messages.ERROR)
            else:
                self.message_user(request, f"{xfer}: status refreshed")

    @admin.action(description="Retry transfer (guarded -- requires confirmation)")
    def retry_transfer(self, request, queryset):
        # Plan Section 9: "'Retry transfer' (guarded, requires
        # re-confirmation since it's money movement)."
        if "confirm" in request.POST:
            form = ConfirmRetryForm(request.POST)
            if form.is_valid():
                for xfer in queryset.filter(status=Transfer.Status.FAILED):
                    try:
                        # Re-send with the SAME externalref (plan Section 11
                        # -- never generate a new one on retry).
                        xfer.status = Transfer.Status.PENDING_APPROVAL
                        xfer.save(update_fields=["status", "updated_at"])
                        services.approve_and_send_transfer(xfer, approved_by=request.user)
                    except Exception as exc:  # noqa: BLE001
                        self.message_user(request, f"{xfer}: retry failed ({exc})", level=messages.ERROR)
                    else:
                        self.message_user(request, f"{xfer}: retried by {request.user}")
                return None
        else:
            form = ConfirmRetryForm()

        return render(
            request,
            "admin/transfers/confirm_retry.html",
            context={
                "transfers": queryset,
                "form": form,
                "action": "retry_transfer",
                "action_checkbox_name": admin.helpers.ACTION_CHECKBOX_NAME,
            },
        )
