"""
Wallets service layer (plan Section 5: "thin wrapper around client").

Every function here: builds the request via moolre_client, persists/updates
the local model, and returns the Django model instance — never the raw API
dict — so callers (views, admin actions, other apps) never touch Moolre's
response shape directly.
"""

from __future__ import annotations

from django.conf import settings
from django.utils import timezone

from apps.moolre_client.client import MoolreClient

from .models import SettlementConfig, Wallet


def _client() -> MoolreClient:
    return MoolreClient.from_settings(settings.MOOLRE)


def create_wallet(
    *,
    accountname: str,
    currency: str | None = None,
    callback_url: str,
    api_enabled: bool = False,
    settlement: dict | None = None,
) -> Wallet:
    """Create a new business wallet via `account/create` and persist it locally.

    Source: docs.moolre.com/ai/create-account.md — success payload includes
    `accountnumber`, `paymentid`, and a one-time `secret` that must be
    captured now (Moolre does not re-display it later).
    """
    client = _client()
    currency = currency or settings.MOOLRE.get("DEFAULT_CURRENCY", "GHS")

    response = client.accounts.create(
        accountname=accountname,
        currency=currency,
        callback=callback_url,
        api=api_enabled,
        settlement=settlement,
    )
    data = response["data"]

    wallet, _ = Wallet.objects.update_or_create(
        accountnumber=data["accountnumber"],
        defaults={
            "accountname": data.get("accountname", accountname),
            "currency": currency,
            "paymentid": data.get("paymentid", ""),
            "api_enabled": bool(data.get("api", 0)),
            "callback_url": callback_url,
            "secret": data.get("secret", ""),
        },
    )

    settlement_data = data.get("settlement") or {}
    if settlement_data:
        SettlementConfig.objects.update_or_create(
            wallet=wallet,
            defaults={
                "frequency": str(settlement_data.get("frequency", "")),
                "channel": str(settlement_data.get("channel", "")),
                "recipient": settlement_data.get("recipient", ""),
                "sublist": settlement_data.get("sublist", ""),
            },
        )
    return wallet


def update_wallet(
    wallet: Wallet,
    *,
    accountname: str | None = None,
    api_enabled: bool | None = None,
    callback_url: str | None = None,
    settlement: dict | None = None,
) -> Wallet:
    """Update wallet/settlement config via `account/update`.

    Note (docs.moolre.com/ai/update-account.md): the endpoint always
    requires `currency="GHS"` regardless of the wallet's own currency.
    """
    client = _client()
    response = client.accounts.update(
        accountnumber=wallet.accountnumber,
        currency="GHS",
        accountname=accountname,
        api=api_enabled,
        callback=callback_url,
        settlement=settlement,
    )
    data = response["data"]

    if accountname is not None:
        wallet.accountname = data.get("accountname", accountname)
    if api_enabled is not None:
        wallet.api_enabled = bool(data.get("api", api_enabled))
    if callback_url is not None:
        wallet.callback_url = data.get("callback", callback_url)
    wallet.save()
    return wallet


def sync_balance(wallet: Wallet) -> Wallet:
    """Refresh `Wallet.balance` via `account/status` (type=1).

    Source: docs.moolre.com/ai/account-status.md — success code SW01.
    """
    client = _client()
    response = client.accounts.status(accountnumber=wallet.accountnumber)
    data = response["data"]

    wallet.balance = data["balance"]
    wallet.last_synced_at = timezone.now()
    wallet.save(update_fields=["balance", "last_synced_at"])
    return wallet


def list_transactions(
    wallet: Wallet,
    *,
    startdate: str | None = None,
    enddate: str | None = None,
    limit: str | None = None,
    status: int | None = None,
) -> list[dict]:
    """List wallet transactions via `account/status` (type=2).

    Source: docs.moolre.com/ai/list-account-transactions.md — success code
    ST08. Returns raw transaction dicts (this domain doesn't persist
    transaction history locally in v1 — see `ledger` app for that, deferred).
    """
    client = _client()
    response = client.accounts.list_transactions(
        accountnumber=wallet.accountnumber,
        startdate=startdate,
        enddate=enddate,
        limit=limit,
        status=status,
    )
    return response["data"].get("transactions", [])
