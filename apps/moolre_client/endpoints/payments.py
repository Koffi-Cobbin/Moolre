"""
Payment / collection endpoints (plan Section 2, "Payment" row group).

Milestone 3 scope: USSD push collection + status check.
Milestone 4 scope: payment links, virtual bank accounts, payment-ID
terminals (all implemented below).

Sources (all confirmed against docs.moolre.com/ai/* during scaffolding):
    - initiate_ussd()/status(): docs.moolre.com/ai/initiate-payment.md,
      payment-status.md -- TR099, TP14, TP13, SS01 (see codes.py).
    - create_payment_id(): docs.moolre.com/ai/create-payment-id.html --
      same physical URL as account/create but type=2 and X-API-PUBKEY
      (not X-API-KEY -- the plan's Account/Payment split in Section 2
      corresponds to different `type` values on the same endpoint).
    - create_virtual_account(): docs.moolre.com/ai/
      create-bank-account-number.html -- account/create, type=9, X-API-PUBKEY.
    - create_payment_link(): docs.moolre.com/ai/generate-payment-link.html --
      POST /embed/link, X-API-PUBKEY, POS09 success / INP02 duplicate.
"""

from __future__ import annotations

from typing import Any


class PaymentsEndpoints:
    def __init__(self, client):
        self._client = client

    def initiate_ussd(
        self,
        *,
        accountnumber: str,
        channel: int,
        currency: str,
        payer: str,
        amount: str,
        externalref: str,
        reference: str | None = None,
        otpcode: str | None = None,
    ) -> dict:
        """POST /open/transact/payment -- USSD push collection request.

        channel is Moolre's MoMo network code (e.g. 13=MTN, 6=Telecel,
        7=AT per docs.moolre.com/ai/initiate-payment.md).

        Pass otpcode to resubmit the *same* externalref after a TP14
        ("OTP required") response -- never generate a new externalref on
        retry (plan Section 11 / idempotency guide).
        """
        payload: dict[str, Any] = {
            "type": 1,
            "accountnumber": accountnumber,
            "channel": channel,
            "currency": currency,
            "payer": payer,
            "amount": amount,
            "externalref": externalref,
        }
        if reference is not None:
            payload["reference"] = reference
        if otpcode is not None:
            payload["otpcode"] = otpcode
        return self._client.request(
            "POST", "/open/transact/payment", key_types=("API_PUBKEY",), json=payload
        )

    def status(self, *, accountnumber: str, id: str, idtype: int = 1) -> dict:
        """POST /open/transact/status -- check a collection's final status.

        idtype: 1 = externalref (recommended, matches what we generate
        client-side), 2 = Moolre-generated transaction id.
        Source: docs.moolre.com/ai/payment-status.md -- success code SS01.
        """
        payload = {
            "type": 1,
            "idtype": idtype,
            "id": id,
            "accountnumber": accountnumber,
        }
        return self._client.request(
            "POST", "/open/transact/status", key_types=("API_PUBKEY",), json=payload
        )

    def create_payment_id(
        self,
        *,
        accountnumber: str,
        phone: str,
        name: str,
        currency: str,
        externalref: str | None = None,
    ) -> dict:
        """POST /open/account/create (type=2) -- reusable *203*id# terminal.

        Source: docs.moolre.com/ai/create-payment-id.html -- success AD14.
        """
        payload: dict[str, Any] = {
            "type": 2,
            "accountnumber": accountnumber,
            "phone": phone,
            "name": name,
            "currency": currency,
        }
        if externalref is not None:
            payload["externalref"] = externalref
        return self._client.request(
            "POST", "/open/account/create", key_types=("API_PUBKEY",), json=payload
        )

    def create_virtual_account(
        self,
        *,
        accountnumber: str,
        currency: str,
        firstname: str,
        lastname: str,
        phone: str,
        email: str,
        uref: str,
        amount: str | None = None,
    ) -> dict:
        """POST /open/account/create (type=9) -- permanent virtual bank account.

        Source: docs.moolre.com/ai/create-bank-account-number.html -- success
        AD19, duplicate-name failure AD32.
        """
        payload: dict[str, Any] = {
            "type": 9,
            "accountnumber": accountnumber,
            "currency": currency,
            "firstname": firstname,
            "lastname": lastname,
            "phone": phone,
            "email": email,
            "uref": uref,
        }
        if amount is not None:
            payload["amount"] = amount
        return self._client.request(
            "POST", "/open/account/create", key_types=("API_PUBKEY",), json=payload
        )

    def create_payment_link(
        self,
        *,
        accountnumber: str,
        amount: str,
        email: str,
        externalref: str,
        currency: str,
        reusable: str = "0",
        callback: str | None = None,
        redirect: str | None = None,
        expiration_time: int | None = None,
        metadata: dict | None = None,
    ) -> dict:
        """POST /embed/link -- generate a hosted Moolre Web POS payment page.

        `reusable`: "0"=single-use, "1"=repeat payments (per docs, this is
        a string, not a bool). Source: docs.moolre.com/ai/
        generate-payment-link.html -- success POS09, duplicate ref INP02.
        """
        payload: dict[str, Any] = {
            "type": 1,
            "accountnumber": accountnumber,
            "amount": amount,
            "email": email,
            "externalref": externalref,
            "currency": currency,
            "reusable": reusable,
        }
        if callback is not None:
            payload["callback"] = callback
        if redirect is not None:
            payload["redirect"] = redirect
        if expiration_time is not None:
            payload["expiration_time"] = expiration_time
        if metadata is not None:
            payload["metadata"] = metadata
        return self._client.request(
            "POST", "/embed/link", key_types=("API_PUBKEY",), json=payload
        )
