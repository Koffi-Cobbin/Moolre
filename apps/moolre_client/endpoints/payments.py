"""
Payment / collection endpoints (plan Section 2, "Payment" row group).

Milestone 3 scope: USSD push collection + status check. Payment links,
virtual accounts, and payment-ID terminals remain Milestone 4 (see the
TODOs still in this module).

Sources:
    - Auth headers: plan Section 2 ("X-API-PUBKEY -- public key (payment
      collection endpoints)"), confirmed against docs.moolre.com/ai/
      payment-status.md which documents X-API-PUBKEY for /open/transact/status.
    - Request shape: plan Section 5's own initiate_ussd_payment() example
      (channel, currency, payer, amount, externalref, reference,
      accountnumber).
    - Response codes: docs.moolre.com/ai/initiate-payment.md -- TR099
      (accepted, awaiting payer action), TP14 (OTP required), TP13
      (duplicate externalref) -- see codes.py.
    - Status response shape: docs.moolre.com/ai/payment-status.md -- SS01,
      idtype (1=externalref, 2=Moolre-generated id).
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

    # TODO(milestone-4): create_payment_id(), create_virtual_account(),
    # create_payment_link() -- payment links, *203*id# terminals, virtual
    # bank accounts (plan Section 2, remaining "Payment" rows).
