"""
Payments (collections) service layer (plan Section 5).

Every function: builds the request via moolre_client, persists/updates the
local model *before and after* the call (write "pending" first so a crash
mid-call is recoverable), and returns the Django model instance -- never
the raw API dict.
"""

from __future__ import annotations

from django.conf import settings
from django.db import transaction

from apps.moolre_client.client import MoolreClient
from apps.moolre_client.codes import MoolreCode
from apps.moolre_client.exceptions import MoolreAPIError
from apps.wallets.models import Wallet

from .models import PaymentIdTerminal, PaymentLink, PaymentRequest, VirtualAccount
from .signals import payment_completed, payment_failed


def _client() -> MoolreClient:
    return MoolreClient.from_settings(settings.MOOLRE)


def initiate_ussd_payment(
    wallet: Wallet,
    *,
    channel: int,
    amount,
    payer_msisdn: str,
    externalref: str,
    reference: str | None = None,
) -> PaymentRequest:
    """Initiate a USSD push collection via `transact/payment`.

    Writes a "pending" `PaymentRequest` row *before* calling Moolre (plan
    Section 5, point 2), so the local record exists even if the process
    crashes mid-call and needs reconciling later.
    """
    payment_request, _ = PaymentRequest.objects.get_or_create(
        externalref=externalref,
        defaults={
            "wallet": wallet,
            "channel": channel,
            "amount": amount,
            "currency": wallet.currency,
            "payer_msisdn": payer_msisdn,
            "status": PaymentRequest.Status.PENDING,
        },
    )

    client = _client()
    try:
        response = client.payments.initiate_ussd(
            accountnumber=wallet.accountnumber,
            channel=channel,
            currency=wallet.currency,
            payer=payer_msisdn,
            amount=str(amount),
            externalref=externalref,
            reference=reference,
        )
    except MoolreAPIError as exc:
        return _handle_initiate_error(payment_request, exc)

    return _apply_initiate_response(payment_request, response)


def confirm_otp(payment_request: PaymentRequest, *, otpcode: str) -> PaymentRequest:
    """Resubmit the *same* externalref with an OTP code after a TP14 response.

    Never generate a new externalref here (plan Section 11).
    """
    client = _client()
    try:
        response = client.payments.initiate_ussd(
            accountnumber=payment_request.wallet.accountnumber,
            channel=payment_request.channel,
            currency=payment_request.currency,
            payer=payment_request.payer_msisdn,
            amount=str(payment_request.amount),
            externalref=payment_request.externalref,
            otpcode=otpcode,
        )
    except MoolreAPIError as exc:
        return _handle_initiate_error(payment_request, exc)

    return _apply_initiate_response(payment_request, response)


def check_payment_status(payment_request: PaymentRequest) -> PaymentRequest:
    """On-demand status refresh via `transact/status` (plan Section 8:
    "on-demand refresh, since polling is deferred to v2").
    """
    client = _client()
    response = client.payments.status(
        accountnumber=payment_request.wallet.accountnumber,
        id=payment_request.externalref,
        idtype=1,
    )
    data = response["data"]

    with transaction.atomic():
        payment_request.transactionid = data.get("transactionid", payment_request.transactionid)
        payment_request.raw_response = response
        txstatus = data.get("txstatus")
        if txstatus == 1:
            _mark_success(payment_request)
        elif txstatus == 2:
            _mark_failed(payment_request)
        else:
            payment_request.save()
    return payment_request


def create_payment_link(
    wallet: Wallet,
    *,
    amount,
    email: str,
    externalref: str,
    reusable: bool = False,
    callback: str | None = None,
    redirect: str | None = None,
    expiration_time: int | None = None,
    metadata: dict | None = None,
) -> PaymentLink:
    """Generate a hosted payment page via `embed/link`.

    Source: docs.moolre.com/ai/generate-payment-link.html.
    """
    client = _client()
    response = client.payments.create_payment_link(
        accountnumber=wallet.accountnumber,
        amount=str(amount),
        email=email,
        externalref=externalref,
        currency=wallet.currency,
        reusable="1" if reusable else "0",
        callback=callback,
        redirect=redirect,
        expiration_time=expiration_time,
        metadata=metadata,
    )
    data = response["data"]
    return PaymentLink.objects.create(
        wallet=wallet,
        externalref=externalref,
        amount=amount,
        currency=wallet.currency,
        authorization_url=data.get("authorization_url", ""),
        reusable=reusable,
        metadata=metadata,
        raw_response=response,
    )


def create_virtual_account(
    wallet: Wallet,
    *,
    firstname: str,
    lastname: str,
    phone: str,
    email: str,
    uref: str,
    amount=None,
) -> VirtualAccount:
    """Create a permanent virtual bank account via `account/create` (type=9).

    Source: docs.moolre.com/ai/create-bank-account-number.html.
    """
    client = _client()
    response = client.payments.create_virtual_account(
        accountnumber=wallet.accountnumber,
        currency=wallet.currency,
        firstname=firstname,
        lastname=lastname,
        phone=phone,
        email=email,
        uref=uref,
        amount=str(amount) if amount is not None else None,
    )
    data = response["data"]
    return VirtualAccount.objects.create(
        wallet=wallet,
        accountno=data.get("accountno", ""),
        accountname=data.get("accountname", ""),
        bankname=data.get("bankname", ""),
        uref=data.get("uref", uref),
        holder_first_name=firstname,
        holder_last_name=lastname,
        phone=phone,
        email=email,
        raw_response=response,
    )


def create_payment_id_terminal(
    wallet: Wallet,
    *,
    phone: str,
    name: str,
    externalref: str | None = None,
) -> PaymentIdTerminal:
    """Create a reusable *203*id# payment terminal via `account/create` (type=2).

    Source: docs.moolre.com/ai/create-payment-id.html.
    """
    client = _client()
    response = client.payments.create_payment_id(
        accountnumber=wallet.accountnumber,
        phone=phone,
        name=name,
        currency=wallet.currency,
        externalref=externalref,
    )
    data = response["data"]
    return PaymentIdTerminal.objects.create(
        wallet=wallet,
        paymentid=data.get("paymentid", ""),
        holder_name=data.get("name", name),
        phone=phone,
        externalref=externalref or "",
        raw_response=response,
    )


def _apply_initiate_response(payment_request: PaymentRequest, response: dict) -> PaymentRequest:
    code = response.get("code")
    data = response.get("data") or {}

    payment_request.raw_response = response
    payment_request.transactionid = data.get("transactionid", payment_request.transactionid)
    payment_request.session_id = data.get("sessionid", payment_request.session_id)

    if MoolreCode.is_otp_required(code):
        payment_request.status = PaymentRequest.Status.OTP_PENDING
        payment_request.otp_required = True
        payment_request.save()
    else:
        # TR099 (accepted, awaiting payer action) or similar -- still
        # pending until the webhook / status check confirms the final
        # outcome (plan Section 6).
        payment_request.status = PaymentRequest.Status.PENDING
        payment_request.save()
    return payment_request


def _handle_initiate_error(payment_request: PaymentRequest, exc: MoolreAPIError) -> PaymentRequest:
    if MoolreCode.is_duplicate_reference(exc.code):
        # TP13: we already sent this externalref -- treat as an idempotent
        # retry acknowledgement, not a hard failure (plan Section 11).
        payment_request.raw_response = exc.raw_response
        payment_request.save(update_fields=["raw_response", "updated_at"])
        return payment_request

    payment_request.raw_response = exc.raw_response
    _mark_failed(payment_request)
    raise exc


def _mark_success(payment_request: PaymentRequest) -> None:
    already_success = payment_request.status == PaymentRequest.Status.SUCCESS
    payment_request.status = PaymentRequest.Status.SUCCESS
    payment_request.save()
    if not already_success:
        payment_completed.send(sender=PaymentRequest, instance=payment_request)


def _mark_failed(payment_request: PaymentRequest) -> None:
    already_failed = payment_request.status == PaymentRequest.Status.FAILED
    payment_request.status = PaymentRequest.Status.FAILED
    payment_request.save()
    if not already_failed:
        payment_failed.send(sender=PaymentRequest, instance=payment_request)
