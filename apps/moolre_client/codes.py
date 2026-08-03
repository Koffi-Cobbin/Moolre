"""
Centralized Moolre response `code` values (plan Section 11).

Codes below were pulled directly from https://docs.moolre.com/ai/ endpoint
pages during scaffolding (not guessed) — see the source comment on each
member. This module is intentionally NOT exhaustive: Moolre's docs don't
publish one master code list, so add new members here as new endpoints are
implemented (Milestones 2-6), rather than scattering literal strings through
`services.py` files.

Usage: map a raw `code` string from a response onto one of these, then
branch in `client.py` / `services.py` on the *meaning* (enum member),
never on the literal string.
"""

from enum import Enum


class MoolreCode(str, Enum):
    # --- Account / wallet (docs: create-account, account-status) ---
    WALLET_CREATED = "WC02"        # account/create success
    WALLET_FOUND = "SW01"          # account/status (type=1) success
    TRANSACTIONS_FOUND = "ST08"    # account/status (type=2) success
    AUTH_API_NOT_ACTIVATED = "AIN04"  # account/status 401 — API access not activated

    # --- Payments / collections (docs: initiate-payment) ---
    OTP_REQUIRED = "TP14"          # USSD push requires OTP confirmation
    PAYMENT_REQUEST_ACCEPTED = "TR099"  # USSD push accepted, awaiting payer action
    DUPLICATE_EXTERNAL_REF = "TP13"     # externalref reused — must retry with SAME ref, not a new one

    # --- Reference / misc data (docs: miscellaneous-data) ---
    REFERENCE_DATA_FOUND = "SD01"  # transact/data success (banks, channels, etc.)

    # --- Webhooks (docs: payment-webhook) ---
    WEBHOOK_PAYMENT_SUCCESS = "P01"  # inbound callback: "Transaction Successful"

    # --- Payment status (docs: payment-status) ---
    PAYMENT_STATUS_FOUND = "SS01"  # transact/status success ("Transaction Successful")

    @classmethod
    def is_otp_required(cls, code: str) -> bool:
        return code == cls.OTP_REQUIRED.value

    @classmethod
    def is_duplicate_reference(cls, code: str) -> bool:
        return code == cls.DUPLICATE_EXTERNAL_REF.value
