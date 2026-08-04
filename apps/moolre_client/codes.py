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

    # --- Payment links (docs: generate-payment-link) ---
    PAYMENT_LINK_CREATED = "POS09"      # embed/link success
    PAYMENT_LINK_DUPLICATE = "INP02"    # duplicate externalref/reference

    # --- Payment IDs / virtual accounts (docs: create-payment-id,
    #     create-bank-account-number) ---
    TERMINAL_CREATED = "AD14"           # account/create (type=2) success -- *203*id# payment ID
    VIRTUAL_ACCOUNT_CREATED = "AD19"    # account/create (type=9) success -- virtual bank account
    VIRTUAL_ACCOUNT_DUPLICATE_NAME = "AD32"  # virtual account creation failed, name already in use

    # --- Transfers / disbursements (docs: validate-name, initiate-transfer,
    #     transfer-status, internal-transfer) ---
    NAME_VALIDATED = "AVD01"        # transact/validate success
    NAME_NOT_FOUND = "AVD02"        # transact/validate: phone/account not found
    TRANSFER_SUCCESS = "OBGH01"     # transact/transfer success (payout completed)
    # TP14, TR099, TP13 (already defined above) are reused by internal_transfer()

    # --- SMS (docs: send-sms, sms-status, sms-account-status,
    #     create-sender-id, sender-id-status, list-sender-ids,
    #     approve-sender-id) ---
    SMS_SENT = "SMS01"                    # sms/send success
    SMS_SENDER_ID_UNAPPROVED = "ASMS07"   # sms/send: sender ID not approved
    SMS_AUTH_ERROR = "AIN01"              # invalid/missing X-API-VASKEY
    SMS_STATUS_FOUND = "ASMQ10"           # sms/status (type=5) success
    SMS_ACCOUNT_STATUS_FOUND = "ASMQ03"   # sms/status (type=2) success -- credit balance
    SMS_SENDER_ID_CREATED = "ASMQ12"      # sms/query (type=3) success
    SMS_SENDER_ID_STATUS_FOUND = "ASMQ01" # sms/status (type=1) success
    SMS_SENDER_ID_LIST_FOUND = "ASMQ08"   # sms/status (type=7) success
    SMS_SENDER_ID_UPDATED = "ASMQ07"      # sms/status (type=6) success -- approve/reject
    SMS_SENDER_ID_PERMISSION_DENIED = "ASMQ09"  # not authorized to approve/reject sender IDs

    # --- WhatsApp (docs: whatsapp-get-templates, whatsapp-send-message,
    #     whatsapp-message-status) ---
    WHATSAPP_SUCCESS = "WAS200"           # generic success across all 3 WhatsApp endpoints
    WHATSAPP_INSUFFICIENT_BALANCE = "WAS401"  # whatsapp/send: WhatsApp bundle exhausted

    @classmethod
    def is_otp_required(cls, code: str) -> bool:
        return code == cls.OTP_REQUIRED.value

    @classmethod
    def is_duplicate_reference(cls, code: str) -> bool:
        return code == cls.DUPLICATE_EXTERNAL_REF.value
