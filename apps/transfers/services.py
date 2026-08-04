"""
Transfers (disbursements) service layer (plan Section 5).

Maker-checker flow (plan Section 8): create_transfer() / create_internal_transfer()
only ever write a local PENDING_APPROVAL row -- Moolre is not called.
approve_and_send_transfer() is the only function that actually sends money,
and it requires an approving user to be passed in explicitly.
"""

from __future__ import annotations

from django.conf import settings
from django.db import transaction as db_transaction
from django.utils import timezone

from apps.moolre_client.client import MoolreClient
from apps.moolre_client.codes import MoolreCode
from apps.moolre_client.exceptions import MoolreAPIError
from apps.wallets.models import Wallet

from .models import NameValidationLog, Transfer
from .signals import transfer_completed, transfer_failed


def _client() -> MoolreClient:
    return MoolreClient.from_settings(settings.MOOLRE)


def validate_name(
    wallet: Wallet, *, receiver: str, channel: str, sublistid: str | None = None
) -> NameValidationLog:
    """Confirm a MoMo/bank holder's name via `transact/validate` before
    creating a transfer (plan Section 8's suggested pre-flight check).

    Source: docs.moolre.com/ai/validate-name.html -- AVD01 success,
    AVD02 not-found.
    """
    client = _client()
    try:
        response = client.transfers.validate_name(
            accountnumber=wallet.accountnumber,
            receiver=receiver,
            channel=channel,
            currency=wallet.currency,
            sublistid=sublistid,
        )
    except MoolreAPIError as exc:
        return NameValidationLog.objects.create(
            receiver=receiver,
            channel=channel,
            status=NameValidationLog.Status.NOT_FOUND,
            raw_response=exc.raw_response,
        )

    return NameValidationLog.objects.create(
        receiver=receiver,
        channel=channel,
        resolved_name=response.get("data", "") if isinstance(response.get("data"), str) else "",
        status=NameValidationLog.Status.FOUND,
        raw_response=response,
    )


def create_transfer(
    wallet: Wallet,
    *,
    channel: str,
    amount,
    receiver: str,
    externalref: str,
    sublistid: str | None = None,
    reference: str | None = None,
    requested_by=None,
) -> Transfer:
    """Write a PENDING_APPROVAL Transfer row. Does NOT call Moolre (plan
    Section 8 maker-checker: nothing is sent until approve_and_send_transfer()).
    """
    return Transfer.objects.create(
        wallet=wallet,
        kind=Transfer.Kind.EXTERNAL,
        channel=channel,
        currency=wallet.currency,
        amount=amount,
        receiver=receiver,
        sublistid=sublistid or "",
        externalref=externalref,
        reference=reference or "",
        requested_by=requested_by,
        status=Transfer.Status.PENDING_APPROVAL,
    )


def create_internal_transfer(
    wallet: Wallet,
    *,
    amount,
    receiver: str,
    externalref: str,
    reference: str | None = None,
    requested_by=None,
) -> Transfer:
    """Write a PENDING_APPROVAL internal Transfer row. Does NOT call Moolre."""
    return Transfer.objects.create(
        wallet=wallet,
        kind=Transfer.Kind.INTERNAL,
        currency=wallet.currency,
        amount=amount,
        receiver=receiver,
        externalref=externalref,
        reference=reference or "",
        requested_by=requested_by,
        status=Transfer.Status.PENDING_APPROVAL,
    )


def reject_transfer(xfer: Transfer, *, rejected_by=None) -> Transfer:
    """Mark a pending transfer as rejected without ever contacting Moolre."""
    if xfer.status != Transfer.Status.PENDING_APPROVAL:
        raise ValueError(f"Cannot reject a transfer in status {xfer.status!r}")
    xfer.status = Transfer.Status.REJECTED
    xfer.approved_by = rejected_by
    xfer.approved_at = timezone.now()
    xfer.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])
    return xfer


def approve_and_send_transfer(xfer: Transfer, *, approved_by) -> Transfer:
    """The ONLY function that actually calls Moolre to move money.

    Requires an approving user (plan Section 8: "full audit logging of who
    triggered it"). Only valid from PENDING_APPROVAL -- calling this twice
    on an already-processed transfer is a no-op guard, not a re-send,
    since externalref must stay stable (plan Section 11).
    """
    if xfer.status != Transfer.Status.PENDING_APPROVAL:
        raise ValueError(
            f"Transfer {xfer.externalref} is not pending approval (status={xfer.status!r})"
        )
    if approved_by is None:
        raise ValueError("approve_and_send_transfer() requires an approving user")

    xfer.approved_by = approved_by
    xfer.approved_at = timezone.now()
    xfer.status = Transfer.Status.PROCESSING
    xfer.save(update_fields=["approved_by", "approved_at", "status", "updated_at"])

    client = _client()
    try:
        if xfer.kind == Transfer.Kind.INTERNAL:
            response = client.transfers.internal_transfer(
                accountnumber=xfer.wallet.accountnumber,
                currency=xfer.currency,
                amount=str(xfer.amount),
                receiver=xfer.receiver,
                externalref=xfer.externalref,
                reference=xfer.reference or None,
            )
            return _apply_internal_response(xfer, response)
        else:
            response = client.transfers.transfer(
                accountnumber=xfer.wallet.accountnumber,
                channel=xfer.channel,
                currency=xfer.currency,
                amount=str(xfer.amount),
                receiver=xfer.receiver,
                externalref=xfer.externalref,
                sublistid=xfer.sublistid or None,
                reference=xfer.reference or None,
            )
            return _apply_external_response(xfer, response)
    except MoolreAPIError as exc:
        return _handle_send_error(xfer, exc)


def confirm_transfer_otp(xfer: Transfer, *, otpcode: str) -> Transfer:
    """Resubmit an internal transfer's *same* externalref with an OTP code
    after a TP14 response. Never generate a new externalref (plan Section 11).
    """
    if xfer.kind != Transfer.Kind.INTERNAL:
        raise ValueError("OTP confirmation only applies to internal transfers")

    client = _client()
    try:
        response = client.transfers.internal_transfer(
            accountnumber=xfer.wallet.accountnumber,
            currency=xfer.currency,
            amount=str(xfer.amount),
            receiver=xfer.receiver,
            externalref=xfer.externalref,
            otpcode=otpcode,
        )
    except MoolreAPIError as exc:
        return _handle_send_error(xfer, exc)
    return _apply_internal_response(xfer, response)


def check_transfer_status(xfer: Transfer) -> Transfer:
    """On-demand status refresh via `transact/status` (plan Section 8:
    "on-demand refresh, since polling is deferred to v2").
    """
    client = _client()
    response = client.transfers.status(
        accountnumber=xfer.wallet.accountnumber, id=xfer.externalref, idtype=1
    )
    data = response["data"]

    with db_transaction.atomic():
        xfer.transactionid = data.get("transactionid", xfer.transactionid)
        xfer.thirdpartyref = data.get("thirdpartyref", xfer.thirdpartyref)
        xfer.raw_response = response
        txstatus = data.get("txstatus")
        if txstatus == 1:
            _mark_success(xfer)
        elif txstatus == 2:
            _mark_failed(xfer)
        else:
            xfer.save()
    return xfer


# -- internal helpers ----------------------------------------------------------


def _apply_external_response(xfer: Transfer, response: dict) -> Transfer:
    data = response.get("data") or {}
    xfer.transactionid = data.get("transactionid", xfer.transactionid)
    xfer.thirdpartyref = data.get("thirdpartyref", xfer.thirdpartyref)
    xfer.fee = data.get("fee", xfer.fee)
    xfer.network_fee = data.get("networkfee", xfer.network_fee)
    xfer.raw_response = response

    if data.get("txstatus") == 1:
        _mark_success(xfer)
    else:
        xfer.status = Transfer.Status.PROCESSING
        xfer.save()
    return xfer


def _apply_internal_response(xfer: Transfer, response: dict) -> Transfer:
    code = response.get("code")
    xfer.raw_response = response

    if MoolreCode.is_otp_required(code):
        xfer.status = Transfer.Status.OTP_PENDING
        xfer.save()
    else:
        # TR099 (accepted) -- still processing until status check/webhook
        # confirms the final outcome.
        xfer.status = Transfer.Status.PROCESSING
        xfer.save()
    return xfer


def _handle_send_error(xfer: Transfer, exc: MoolreAPIError) -> Transfer:
    if MoolreCode.is_duplicate_reference(exc.code):
        # TP13: already sent -- idempotent retry ack, not a hard failure.
        xfer.raw_response = exc.raw_response
        xfer.save(update_fields=["raw_response", "updated_at"])
        return xfer

    xfer.raw_response = exc.raw_response
    _mark_failed(xfer)
    raise exc


def _mark_success(xfer: Transfer) -> None:
    already_success = xfer.status == Transfer.Status.SUCCESS
    xfer.status = Transfer.Status.SUCCESS
    xfer.save()
    if not already_success:
        transfer_completed.send(sender=Transfer, instance=xfer)


def _mark_failed(xfer: Transfer) -> None:
    already_failed = xfer.status == Transfer.Status.FAILED
    xfer.status = Transfer.Status.FAILED
    xfer.save()
    if not already_failed:
        transfer_failed.send(sender=Transfer, instance=xfer)
