"""
Core HTTP client for the Moolre API.

Zero Django dependencies (plan Section 3) — configuration is passed in
explicitly via `MoolreClient(config=...)` / `MoolreClient.from_settings()`,
never imported from `django.conf`.

Auth headers (plan Section 2):
    X-API-USER    always required
    X-API-KEY     transfers, account admin
    X-API-PUBKEY  payment collection endpoints
    X-API-VASKEY  SMS / WhatsApp
"""

from __future__ import annotations

import logging
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .exceptions import (
    MoolreAPIError,
    MoolreAuthError,
    MoolreNetworkError,
    MoolreValidationError,
)

logger = logging.getLogger("moolre_client")

# Response `status` values Moolre uses to mean "the call itself failed"
# (as opposed to `code`, which is the more specific reason). Seen in the
# docs as both int 0/1 and string "0"/"1" depending on endpoint, so we
# normalize with `str(...)` before comparing.
_FAILURE_STATUSES = {"0"}


class MoolreClient:
    """Thin wrapper around the Moolre REST API.

    Not meant to be instantiated directly in most call sites — use
    `MoolreClient.from_settings(config)` (Django apps typically build
    `config` from `settings.MOOLRE`, see `apps/*/services.py`).
    """

    def __init__(self, *, config: dict[str, Any], http_client: httpx.Client | None = None):
        self._config = config
        environment = config.get("ENVIRONMENT", "sandbox")
        base_urls = config.get("BASE_URL", {})
        base_url = base_urls.get(environment)
        if not base_url:
            raise MoolreAuthError(
                f"No BASE_URL configured for environment {environment!r}"
            )
        self._environment = environment
        self._base_url = base_url.rstrip("/")
        self._timeout = config.get("TIMEOUT", 15)
        self._max_retries = config.get("MAX_RETRIES", 3)
        self._http = http_client or httpx.Client(timeout=self._timeout)

        # Endpoint groups (plan Section 3 structure) — imported lazily to
        # avoid a circular import (endpoints/*.py don't import client.py at
        # module scope, but this keeps the dependency direction obvious).
        from .endpoints.accounts import AccountsEndpoints
        from .endpoints.misc import MiscEndpoints
        from .endpoints.payments import PaymentsEndpoints
        from .endpoints.sms import SmsEndpoints
        from .endpoints.transfers import TransfersEndpoints
        from .endpoints.whatsapp import WhatsAppEndpoints

        self.accounts = AccountsEndpoints(self)
        self.misc = MiscEndpoints(self)
        self.transfers = TransfersEndpoints(self)  # placeholder, milestone 5
        self.payments = PaymentsEndpoints(self)    # placeholder, milestones 3-4
        self.sms = SmsEndpoints(self)               # placeholder, milestone 6
        self.whatsapp = WhatsAppEndpoints(self)     # placeholder, milestone 6

    # -- construction helpers -------------------------------------------------

    @classmethod
    def from_settings(cls, config: dict[str, Any]) -> "MoolreClient":
        """Build a client from a `MOOLRE` config dict (plan Section 10)."""
        return cls(config=config)

    @classmethod
    def for_wallet(cls, wallet) -> "MoolreClient":
        """Convenience constructor used from `services.py` call sites.

        Moolre credentials (API_USER/KEY/PUBKEY/VASKEY) are per-integration,
        not per-wallet — a single Moolre login can own several business
        wallets/accounts. This constructor exists so service functions can
        write `MoolreClient.for_wallet(wallet)` without reaching into Django
        settings themselves; it resolves the same global config either way.
        `wallet` is accepted for future-proofing (e.g. if Moolre ever issues
        per-wallet sub-credentials) and isn't otherwise used yet.
        """
        from django.conf import settings  # local import: keeps this file importable without Django

        return cls.from_settings(settings.MOOLRE)

    # -- auth header sets (plan Section 2) ------------------------------------

    def _headers(self, *, key_types: tuple[str, ...]) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        api_user = self._config.get("API_USER")
        if not api_user:
            raise MoolreAuthError("MOOLRE API_USER is not configured")
        headers["X-API-USER"] = api_user

        # Plan Section 2: "Sandbox ... only X-API-USER required; VAS key
        # still needed for SMS/WhatsApp" — so API_KEY and API_PUBKEY are
        # both optional in sandbox, but API_VASKEY is always required.
        _sandbox_optional = {"API_KEY", "API_PUBKEY"}

        for key_type in key_types:
            value = self._config.get(key_type)
            optional_here = (
                self._environment == "sandbox" and key_type in _sandbox_optional
            )
            if not value and not optional_here:
                raise MoolreAuthError(f"MOOLRE {key_type} is not configured")
            if value:
                header_name = {
                    "API_KEY": "X-API-KEY",
                    "API_PUBKEY": "X-API-PUBKEY",
                    "API_VASKEY": "X-API-VASKEY",
                }[key_type]
                headers[header_name] = value
        return headers

    # -- request plumbing ------------------------------------------------------

    def _should_retry(self, exc: BaseException) -> bool:
        # Safe retries only (plan Section 11): network errors / timeouts / 5xx.
        if isinstance(exc, MoolreNetworkError):
            return True
        return False

    def request(
        self,
        method: str,
        path: str,
        *,
        key_types: tuple[str, ...],
        json: dict | None = None,
        params: dict | None = None,
    ) -> dict:
        """Make an authenticated request and return the parsed response body.

        Raises:
            MoolreAuthError: missing/invalid credentials
            MoolreValidationError: 4xx (except auth) — do NOT retry blindly
            MoolreNetworkError: connection/timeout — safe to retry
            MoolreAPIError: HTTP 200 but Moolre's own envelope signals failure
        """
        headers = self._headers(key_types=key_types)
        url = f"{self._base_url}{path}"

        @retry(
            reraise=True,
            stop=stop_after_attempt(self._max_retries),
            wait=wait_exponential(multiplier=0.5, max=8),
            retry=retry_if_exception_type(MoolreNetworkError),
        )
        def _do_request():
            try:
                response = self._http.request(
                    method, url, headers=headers, json=json, params=params
                )
            except httpx.TimeoutException as exc:
                raise MoolreNetworkError(f"Timeout calling {url}") from exc
            except httpx.TransportError as exc:
                raise MoolreNetworkError(f"Network error calling {url}") from exc

            if response.status_code >= 500:
                raise MoolreNetworkError(
                    f"Moolre returned {response.status_code} for {url}"
                )
            if response.status_code in (401, 403):
                raise MoolreAuthError(
                    f"Moolre auth error {response.status_code} for {url}: {response.text}"
                )
            if response.status_code >= 400:
                body = _safe_json(response)
                raise MoolreValidationError(
                    body.get("message") if isinstance(body, dict) else response.text,
                    code=body.get("code") if isinstance(body, dict) else None,
                    raw_response=body,
                )
            return response

        response = _do_request()
        body = _safe_json(response)

        if isinstance(body, dict) and str(body.get("status")) in _FAILURE_STATUSES:
            raise MoolreAPIError(
                _stringify_message(body.get("message")),
                code=body.get("code"),
                raw_response=body,
            )
        return body

    def close(self):
        self._http.close()


def _safe_json(response: httpx.Response):
    try:
        return response.json()
    except ValueError:
        return {"raw_text": response.text}


def _stringify_message(message) -> str:
    if isinstance(message, list):
        return " ".join(str(m) for m in message)
    return str(message) if message is not None else "Moolre API error"
