"""
Account / wallet endpoints (plan Section 2, "Account" row group).

Sources (fetched from docs.moolre.com/ai/ during scaffolding):
    create-account.md, update-account.md, account-status.md,
    list-account-transactions.md

All four live under two physical Moolre URLs:
    POST /open/account/create   -> create()
    POST /open/account/update   -> update()
    POST /open/account/status   -> status()          (type=1, balance)
    POST /open/account/status   -> list_transactions() (type=2)
"""

from __future__ import annotations

from typing import Any


class AccountsEndpoints:
    def __init__(self, client):
        self._client = client

    def create(
        self,
        *,
        accountname: str,
        currency: str,
        callback: str,
        api: bool | None = None,
        settlement: dict | None = None,
    ) -> dict:
        """POST /open/account/create — create a new business wallet.

        Success response includes the wallet's `secret` (store encrypted,
        plan Section 10) and `accountnumber` — see WC02 in codes.py.
        """
        payload: dict[str, Any] = {
            "type": 1,
            "accountname": accountname,
            "currency": currency,
            "callback": callback,
            "settlement": settlement or {},
        }
        if api is not None:
            payload["api"] = api
        return self._client.request(
            "POST", "/open/account/create", key_types=("API_KEY",), json=payload
        )

    def update(
        self,
        *,
        accountnumber: str,
        currency: str = "GHS",
        accountname: str | None = None,
        api: bool | None = None,
        callback: str | None = None,
        settlement: dict | None = None,
    ) -> dict:
        """POST /open/account/update — update wallet/settlement config.

        Note (per docs): `currency` is always required and the endpoint
        currently only accepts "GHS" here regardless of the wallet's own
        currency.
        """
        payload: dict[str, Any] = {
            "type": 1,
            "accountnumber": accountnumber,
            "currency": currency,
        }
        if accountname is not None:
            payload["accountname"] = accountname
        if api is not None:
            payload["api"] = api
        if callback is not None:
            payload["callback"] = callback
        if settlement is not None:
            payload["settlement"] = settlement
        return self._client.request(
            "POST", "/open/account/update", key_types=("API_KEY",), json=payload
        )

    def status(self, *, accountnumber: str) -> dict:
        """POST /open/account/status (type=1) — check wallet balance."""
        payload = {"type": 1, "accountnumber": accountnumber}
        return self._client.request(
            "POST", "/open/account/status", key_types=("API_KEY",), json=payload
        )

    def list_transactions(
        self,
        *,
        accountnumber: str,
        startdate: str | None = None,
        enddate: str | None = None,
        limit: str | None = None,
        status: int | None = None,
    ) -> dict:
        """POST /open/account/status (type=2) — list wallet transactions.

        `status` filter per docs: 0=Pending, 1=Successful, 2=Failed.
        """
        payload: dict[str, Any] = {"type": 2, "accountnumber": accountnumber}
        if startdate is not None:
            payload["startdate"] = startdate
        if enddate is not None:
            payload["enddate"] = enddate
        if limit is not None:
            payload["limit"] = limit
        if status is not None:
            payload["status"] = status
        return self._client.request(
            "POST", "/open/account/status", key_types=("API_KEY",), json=payload
        )
