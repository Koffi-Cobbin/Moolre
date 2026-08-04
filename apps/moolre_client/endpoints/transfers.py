"""
Transfer / disbursement endpoints (plan Section 2, "Transfer" row group).

Sources (confirmed against docs.moolre.com/ai/* during scaffolding):
    - validate_name(): validate-name.html -- POST /open/transact/validate,
      X-API-KEY (accepts public or private key). Channel codes for
      transfers are 1=MTN, 6=Telecel, 7=AT, 2=Instant Bank Transfer --
      NOTE these differ from the USSD *collection* channel codes seen on
      initiate-payment.html (13=MTN, 6=Telecel, 7=AT). Don't conflate the
      two -- transfers and collections use separate channel enumerations.
    - transfer(): initiate-transfer.html -- POST /open/transact/transfer,
      X-API-KEY (private key only). Synchronous: success code OBGH01
      returns the final txstatus directly, no separate OTP step observed
      in the docs for this endpoint (unlike internal_transfer()).
    - status(): transfer-status.html -- POST /open/transact/status,
      X-API-KEY. Same physical URL as payments.status() but documented
      separately for transfers; SS01 success.
    - internal_transfer(): internal-transfer.html -- POST
      /open/transact/internal, X-API-KEY (private key only). Has the same
      TP14 (OTP required) / TR099 (accepted) / TP13 (duplicate ref) flow
      as USSD collections.
"""

from __future__ import annotations

from typing import Any


class TransfersEndpoints:
    def __init__(self, client):
        self._client = client

    def validate_name(
        self,
        *,
        accountnumber: str,
        receiver: str,
        channel: str,
        currency: str,
        sublistid: str | None = None,
    ) -> dict:
        """POST /open/transact/validate -- confirm a MoMo/bank holder's name.

        channel: "1"=MTN, "6"=Telecel, "7"=AT, "2"=Instant Bank Transfer
        (transfer-specific codes, per validate-name.html).
        """
        payload: dict[str, Any] = {
            "type": 1,
            "receiver": receiver,
            "channel": channel,
            "currency": currency,
            "accountnumber": accountnumber,
        }
        if sublistid is not None:
            payload["sublistid"] = sublistid
        return self._client.request(
            "POST", "/open/transact/validate", key_types=("API_KEY",), json=payload
        )

    def transfer(
        self,
        *,
        accountnumber: str,
        channel: str,
        currency: str,
        amount: str,
        receiver: str,
        externalref: str,
        sublistid: str | None = None,
        reference: str | None = None,
    ) -> dict:
        """POST /open/transact/transfer -- payout to MoMo or bank.

        Source: docs.moolre.com/ai/initiate-transfer.html -- success OBGH01,
        response `data` includes txstatus, transactionid, fee, networkfee.
        """
        payload: dict[str, Any] = {
            "type": 1,
            "channel": channel,
            "currency": currency,
            "amount": amount,
            "receiver": receiver,
            "externalref": externalref,
            "accountnumber": accountnumber,
        }
        if sublistid is not None:
            payload["sublistid"] = sublistid
        if reference is not None:
            payload["reference"] = reference
        return self._client.request(
            "POST", "/open/transact/transfer", key_types=("API_KEY",), json=payload
        )

    def status(self, *, accountnumber: str, id: str, idtype: int = 1) -> dict:
        """POST /open/transact/status -- check a transfer's final status.

        Source: docs.moolre.com/ai/transfer-status.html -- success SS01.
        """
        payload = {
            "type": 1,
            "idtype": idtype,
            "id": id,
            "accountnumber": accountnumber,
        }
        return self._client.request(
            "POST", "/open/transact/status", key_types=("API_KEY",), json=payload
        )

    def internal_transfer(
        self,
        *,
        accountnumber: str,
        currency: str,
        amount: str,
        receiver: str,
        externalref: str,
        reference: str | None = None,
        otpcode: str | None = None,
    ) -> dict:
        """POST /open/transact/internal -- wallet-to-wallet transfer.

        Source: docs.moolre.com/ai/internal-transfer.html -- TP14 (OTP
        required), TR099 (accepted), TP13 (duplicate externalref). Pass
        `otpcode` to resubmit the *same* externalref after a TP14 response.
        """
        payload: dict[str, Any] = {
            "type": 1,
            "currency": currency,
            "amount": amount,
            "receiver": receiver,
            "externalref": externalref,
            "accountnumber": accountnumber,
        }
        if reference is not None:
            payload["reference"] = reference
        if otpcode is not None:
            payload["otpcode"] = otpcode
        return self._client.request(
            "POST", "/open/transact/internal", key_types=("API_KEY",), json=payload
        )
