"""
Webhook verification helpers.

Moolre's documented payment webhook (docs.moolre.com/ai/payment-webhook)
does not currently publish a request-signing scheme (no HMAC header is
documented) — the payload is just `{status, code, message, data}` posted
to the callback URL you registered on the wallet.

Per plan Section 6 ("verify, don't trust"), the recommended safeguard in
the absence of a signature is: treat the webhook as a *hint* to re-check,
not as ground truth. `verify_via_status_check()` re-fetches the
transaction/transfer status from Moolre directly and only trusts that.

If Moolre later documents a shared-secret / HMAC signature header, add a
`verify_signature()` function here and switch webhook views (plan Section 6)
to prefer it over the status-check round-trip.
"""

from __future__ import annotations

from typing import Any, Callable

from .exceptions import MoolreValidationError

REQUIRED_WEBHOOK_FIELDS = ("status", "code", "message", "data")


def validate_shape(payload: dict[str, Any]) -> None:
    """Check the inbound payload has the fields Moolre's webhook doc promises.

    Raises MoolreValidationError if the payload doesn't look like a Moolre
    callback at all, so callers can 400 fast instead of processing garbage.
    """
    missing = [f for f in REQUIRED_WEBHOOK_FIELDS if f not in payload]
    if missing:
        raise MoolreValidationError(
            f"Webhook payload missing required field(s): {', '.join(missing)}",
            raw_response=payload,
        )


def verify_via_status_check(
    externalref: str,
    *,
    status_check_fn: Callable[[str], dict],
) -> dict:
    """Re-fetch the authoritative status from Moolre rather than trusting the
    webhook body outright (plan Section 6: "verify, don't trust").

    `status_check_fn` should be something like
    `apps.payments.services.check_payment_status` / the `transact/status`
    endpoint wrapper — passed in rather than imported here to keep this
    module free of Django/app dependencies.
    """
    return status_check_fn(externalref)
