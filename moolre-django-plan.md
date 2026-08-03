# Django App Plan: Moolre Payments & Messaging Platform

Source: [docs.moolre.com](https://docs.moolre.com/) (Moolre AI Documentation Index, `llms-full.txt`)

Moolre is a Ghanaian fintech API covering **wallets/accounts**, **mobile money & bank transfers/collections**, **hosted payment links**, **SMS**, and **WhatsApp** messaging, plus **USSD**. This plan lays out a Django project that wraps these services into a reusable internal platform (a payments/comms backend other apps or a dashboard can consume).

---

## 1. Goals & Scope

Build a Django app (`moolre`) that:

- Manages one or more Moolre **business wallets** (create/update/check balance/list transactions)
- Sends and tracks **collections** (mobile money USSD push, hosted payment links, virtual bank accounts)
- Sends and tracks **disbursements** (transfers to mobile money / bank, internal transfers)
- Sends **SMS** and **WhatsApp** messages and tracks delivery status
- Receives and verifies **webhooks** (payment callbacks) idempotently
- Exposes a clean internal Django ORM/service layer + optional REST API + admin dashboard
- Is safe to run against **sandbox** and **live** environments via configuration

Out of scope (v1): USSD app hosting itself (Moolre hosts the USSD shortcode; we only initiate/receive results), multi-currency FX.

---

## 2. Moolre API Surface (what we're wrapping)

| Domain | Endpoint | Method | Purpose |
|---|---|---|---|
| Account | `/open/account/create` | POST | Create a business wallet |
| Account | `/open/account/update` | POST | Update wallet/settlement config |
| Account | `/open/account/status` (type=1) | POST | Check wallet balance |
| Account | `/open/account/status` (type=2) | POST | List transactions |
| Transfer | `/open/transact/validate` | POST | Validate MoMo/bank account holder name |
| Transfer | `/open/transact/transfer` | POST | Payout to MoMo (MTN/Telecel/AT) or bank |
| Transfer | `/open/transact/status` | POST | Check transfer status |
| Transfer | `/open/transact/internal` | POST | Internal wallet-to-wallet transfer |
| Payment | `/open/transact/payment` | POST | USSD push collection request |
| Payment | `/open/account/create` (type=2) | POST | Create reusable payment ID (`*203*id#`) |
| Payment | `/open/account/create` (type=9) | POST | Create virtual bank account for collections |
| Payment | `/embed/link` | POST | Generate hosted payment link |
| Payment | `/open/transact/status` | POST | Check payment/collection status |
| Payment | *(your server)* | POST (inbound) | Webhook/callback receiver |
| SMS | `/open/sms/send` | POST/GET | Send SMS (bulk or single) |
| SMS | `/open/sms/status` | POST | Delivery status / balance / sender ID mgmt |
| SMS | `/open/sms/query` | POST | Create sender ID |
| WhatsApp | `/open/whatsapp/template` | GET | Fetch approved templates |
| WhatsApp | `/open/whatsapp/send` | POST | Send templated messages |
| WhatsApp | `/open/whatsapp/status` | POST | Delivery status |
| Misc | `/open/transact/data` | GET | Reference data (banks, channels) |

**Environments**
- Live: `https://api.moolre.com`
- Sandbox: `https://sandbox.moolre.com` (only `X-API-USER` required; VAS key still needed for SMS/WhatsApp)

**Auth headers**
- `X-API-USER` — Moolre username (always)
- `X-API-KEY` — private key (transfers, account admin)
- `X-API-PUBKEY` — public key (payment collection endpoints)
- `X-API-VASKEY` — SMS/WhatsApp key

---

## 3. Project Structure

```
moolre_project/
├── manage.py
├── config/                     # Django project settings
│   ├── settings/
│   │   ├── base.py
│   │   ├── dev.py
│   │   └── prod.py
│   ├── urls.py
│   └── celery.py
├── apps/
│   ├── moolre_client/          # Thin API client (no Django models) — reusable/pip-installable
│   │   ├── client.py           # requests/httpx wrapper, auth, retries
│   │   ├── exceptions.py
│   │   ├── endpoints/
│   │   │   ├── accounts.py
│   │   │   ├── transfers.py
│   │   │   ├── payments.py
│   │   │   ├── sms.py
│   │   │   ├── whatsapp.py
│   │   │   └── misc.py
│   │   └── signing.py          # webhook signature/verification helpers
│   ├── wallets/                 # Account/wallet domain
│   │   ├── models.py            # Wallet, Settlement
│   │   ├── services.py          # create_wallet(), sync_balance(), list_transactions()
│   │   └── admin.py
│   ├── payments/                 # Collections domain
│   │   ├── models.py            # PaymentRequest, PaymentLink, VirtualAccount, PaymentIdTerminal
│   │   ├── services.py          # initiate_ussd_payment(), create_payment_link(), create_virtual_account()
│   │   ├── webhooks.py           # verify + handle inbound callback
│   │   └── admin.py
│   ├── transfers/                 # Disbursements domain
│   │   ├── models.py             # Transfer, NameValidation
│   │   ├── services.py           # validate_name(), send_transfer(), internal_transfer()
│   │   └── admin.py
│   ├── messaging/                  # SMS + WhatsApp domain
│   │   ├── models.py              # SmsMessage, SenderId, WhatsAppTemplate, WhatsAppMessage
│   │   ├── services.py
│   │   └── admin.py
│   ├── ledger/                      # Optional: internal double-entry bookkeeping / reconciliation
│   │   └── models.py
│   └── api/                          # DRF layer exposing internal endpoints to other apps/frontends
│       ├── serializers.py
│       ├── views.py
│       └── urls.py
├── tasks/                              # Celery tasks: polling, retries, reconciliation
│   ├── payments.py
│   ├── transfers.py
│   └── messaging.py
└── tests/
    ├── fixtures/                        # Recorded sandbox JSON responses
    └── ...
```

**Design principle:** `moolre_client` has zero Django dependencies — it's a pure Python SDK. Django apps (`wallets`, `payments`, `transfers`, `messaging`) each own their models + call into the client via `services.py`. This keeps the Moolre integration testable and reusable outside Django if needed.

---

## 4. Data Models (per domain)

### `wallets`
- `Wallet(accountnumber, accountname, currency, paymentid, api_enabled, callback_url, secret, balance, last_synced_at)`
- `SettlementConfig(wallet FK, frequency, channel, recipient, sublist)`

### `payments` (collections)
- `PaymentRequest(wallet FK, channel, amount, currency, payer_msisdn, externalref UNIQUE, transactionid, status, otp_required, session_id, created_at, updated_at)`
- `PaymentLink(wallet FK, externalref UNIQUE, amount, currency, authorization_url, reusable, expires_at, metadata JSON, status)`
- `VirtualAccount(wallet FK, accountno, accountname, bankname, uref UNIQUE, holder_first_name, holder_last_name, phone, email)`
- `PaymentIdTerminal(wallet FK, paymentid, holder_name, phone, externalref)`
- `WebhookEvent(raw_payload JSON, signature, verified BOOL, processed BOOL, received_at)` — append-only audit log of every inbound callback, processed idempotently

### `transfers` (disbursements)
- `NameValidationLog(receiver, channel, resolved_name, status, created_at)`
- `Transfer(wallet FK, channel, currency, amount, receiver, sublistid, externalref UNIQUE, reference, transactionid, thirdpartyref, status, fee, network_fee, created_at, updated_at)`

### `messaging`
- `SenderId(name, approval_status, whitelisted)`
- `SmsMessage(senderid FK, recipient, message, ref UNIQUE, status, sent_at)`
- `WhatsAppTemplate(template_id, name, language, status, body, placeholders JSON)`
- `WhatsAppMessage(template FK, recipient, ref UNIQUE, placeholders JSON, status)`

All transactional models get:
- `externalref` / `ref` as **unique** fields → enforce idempotency at the DB level, matching Moolre's own dedup rules (`TP13` duplicate-reference error)
- `status` choices mirroring Moolre's `txstatus` (0=Pending, 1=Success, 2=Failed)
- timestamps + a generic `raw_response JSONField` to store the last raw API payload for debugging

---

## 5. Core Service Layer (business logic, thin wrapper around client)

```python
# apps/payments/services.py
from apps.moolre_client.client import MoolreClient

def initiate_ussd_payment(wallet, *, channel, amount, payer_msisdn, externalref, reference=None):
    client = MoolreClient.for_wallet(wallet)
    resp = client.payments.initiate(
        channel=channel, currency=wallet.currency, payer=payer_msisdn,
        amount=str(amount), externalref=externalref, reference=reference,
        accountnumber=wallet.accountnumber,
    )
    return PaymentRequest.objects.update_or_create(
        externalref=externalref,
        defaults={...}
    )
```

Every service function:
1. Builds the request via `moolre_client`
2. Persists/updates the local model **before and after** the call (write "pending" row first, so a crash mid-call is still recoverable/reconcilable)
3. Returns the Django model instance, not the raw API dict

---

## 6. Webhooks / Callbacks

- Single endpoint per domain, e.g. `POST /webhooks/moolre/payments/`
- On receipt:
  1. Store raw payload in `WebhookEvent` immediately (before any processing) for audit/replay
  2. Validate shape (`status`, `code`, `data.externalref`/`transactionid`)
  3. Look up matching `PaymentRequest`/`Transfer` by `externalref`; update status idempotently (safe to receive the same callback twice)
  4. Fire a Django signal (`payment_completed`, `payment_failed`) so other apps can react (e.g. unlock an order, top up credits)
  5. Return `200` quickly; do heavier follow-up work (notifications, ledger posting) in a Celery task
- CSRF-exempt, but protect via:
  - IP allow-list (if Moolre publishes static IPs) and/or
  - Shared-secret verification: compare the wallet's `secret`/callback token if Moolre includes one, else validate by re-fetching status via `/open/transact/status` before trusting a callback ("verify, don't trust")

---

## 7. Background Jobs (Celery) — **Deferred to v2**

Not part of the v1 build. v1 relies on synchronous API calls plus webhooks for status updates; anything not covered by a webhook is checked on-demand (e.g. a manual "refresh status" action in the admin/API) rather than polled automatically.

Noted here for future scope — **build in v2**:

| Task | Trigger | Purpose |
|---|---|---|
| `poll_pending_payments` | every 1–2 min | For any `PaymentRequest`/`Transfer` still pending after N minutes, call status endpoint as a safety net in case a webhook was missed |
| `sync_wallet_balances` | every 5–15 min or on-demand | Refresh cached `Wallet.balance` |
| `sync_sms_status` / `sync_whatsapp_status` | every few min, batched | Batch-check `ref` arrays for messages still "sent" |
| `retry_failed_dispatch` | on failure w/ backoff | Retries Moolre calls that failed on network/5xx errors — **never** retries with a new `externalref` (must reuse the same one to stay idempotent) |
| `reconcile_transactions` | nightly | Cross-check local ledger vs `list_transactions` for each wallet |

v1 mitigation in place of polling: webhook handlers still do the state updates (Section 6), and the REST API layer (Section 8) exposes on-demand "check status" endpoints so a frontend/service can pull the latest state whenever it needs to, rather than the backend pushing it on a schedule.

---

## 8. REST API Layer (for frontend/other services)

Goal: a consumer (web frontend, mobile app, another microservice) should **never need to call Moolre directly or know Moolre's request/response shapes** — every action and status check available in `moolre_client` is mirrored here, so the whole system in Section 2 is reachable through this layer. Endpoints are grouped by domain and, where useful, mapped back to the underlying Moolre call.

### Wallets
| Endpoint | Method | Moolre call behind it |
|---|---|---|
| `/api/wallets/` | GET | list local wallets |
| `/api/wallets/` | POST | `account/create` |
| `/api/wallets/{id}/` | GET | local record |
| `/api/wallets/{id}/` | PATCH | `account/update` |
| `/api/wallets/{id}/balance/` | GET | `account/status` (type=1) |
| `/api/wallets/{id}/transactions/` | GET (filters: `status`, `start`, `end`, `limit`) | `account/status` (type=2) |

### Collections (payments)
| Endpoint | Method | Moolre call behind it |
|---|---|---|
| `/api/payments/ussd/` | POST | `transact/payment` (USSD push collection) |
| `/api/payments/ussd/{externalref}/confirm-otp/` | POST | resubmits `transact/payment` with `otpcode` when `TP14` was returned |
| `/api/payments/links/` | POST | `embed/link` (generate hosted payment link) |
| `/api/payments/links/{externalref}/` | GET | local record + link status |
| `/api/payments/virtual-accounts/` | POST | `account/create` (type=9, virtual bank account) |
| `/api/payments/virtual-accounts/` | GET | list local virtual accounts |
| `/api/payments/payment-ids/` | POST | `account/create` (type=2, reusable `*203*id#` payment ID) |
| `/api/payments/payment-ids/` | GET | list local payment ID terminals |
| `/api/payments/{externalref}/status/` | GET | `transact/status` (on-demand refresh, since polling is deferred to v2 — see Section 7) |
| `/webhooks/moolre/payments/` | POST (inbound) | receives Moolre's payment callback (Section 6) |

### Disbursements (transfers)
| Endpoint | Method | Moolre call behind it |
|---|---|---|
| `/api/transfers/validate-name/` | POST | `transact/validate` (confirm MoMo/bank holder name before payout) |
| `/api/transfers/` | POST | `transact/transfer` (payout to MoMo/bank) — gated by permission/approval, see below |
| `/api/transfers/internal/` | POST | `transact/internal` (wallet-to-wallet) |
| `/api/transfers/{externalref}/confirm-otp/` | POST | resubmits with `otpcode` when `TP14` was returned |
| `/api/transfers/{externalref}/` | GET | local record |
| `/api/transfers/{externalref}/status/` | GET | `transact/status` (on-demand refresh) |
| `/api/transfers/` | GET (filters: `status`, `channel`, `date range`) | local list |

### Messaging — SMS
| Endpoint | Method | Moolre call behind it |
|---|---|---|
| `/api/sms/` | POST | `sms/send` (single or bulk; accepts an array of recipients) |
| `/api/sms/{ref}/status/` | GET | `sms/status` (type=5) |
| `/api/sms/account-status/` | GET | `sms/status` (type=2, credit balance) |
| `/api/sms/sender-ids/` | GET | `sms/status` (type=7, list sender IDs) |
| `/api/sms/sender-ids/` | POST | `sms/query` (type=3, request new sender ID) |
| `/api/sms/sender-ids/{id}/status/` | GET | `sms/status` (type=1) |
| `/api/sms/sender-ids/{id}/approve/` | POST | `sms/status` (type=6, approve/reject — admin/staff only) |

### Messaging — WhatsApp
| Endpoint | Method | Moolre call behind it |
|---|---|---|
| `/api/whatsapp/templates/` | GET | `whatsapp/template` (fetch approved templates, cached locally) |
| `/api/whatsapp/messages/` | POST | `whatsapp/send` (batch templated send) |
| `/api/whatsapp/messages/{ref}/status/` | GET | `whatsapp/status` |
| `/api/whatsapp/messages/status/bulk/` | POST (array of refs) | `whatsapp/status` batch check |

### Reference / misc
| Endpoint | Method | Moolre call behind it |
|---|---|---|
| `/api/reference/banks/` | GET (`?country=gha`) | `transact/data` (`data=banks`) |
| `/api/reference/channels/` | GET | `transact/data` (mobile money channels etc.) |

### Cross-cutting API concerns
- **Consistent envelope**: every response normalizes Moolre's `status/code/message/data` shape into a single internal schema (e.g. `{ "success": bool, "code": str, "message": str, "data": {...} }`) so consumers never parse Moolre-specific codes directly.
- **Idempotency at the edge**: `POST` endpoints that create money-moving or messaging requests accept an optional client-supplied `Idempotency-Key` / `externalref`; if omitted, the API generates one and returns it, so a frontend can safely retry a request without double-sending.
- **AuthN/Z tiers**:
  - Read endpoints (`balance`, `status`, `transactions`, `templates`, `reference data`) — any authenticated internal client
  - Messaging sends (SMS/WhatsApp) — internal service-to-service tokens, rate-limited
  - Transfers/disbursements — highest tier: separate permission class, optional maker-checker/approval step before the transfer is actually sent to Moolre, and full audit logging of who triggered it
- **OpenAPI schema** (via `drf-spectacular`) generated from these views so other teams/services can generate their own client from a single source of truth, mirroring how Moolre publishes machine-readable docs.

---

## 9. Django Admin

Register all models with:
- Read-only fields for anything synced from Moolre (`status`, `transactionid`, `raw_response`)
- List filters on `status`, `channel`, `created_at`
- Admin actions: "Re-check status", "Resend webhook processing" (for debugging), "Retry transfer" (guarded, requires re-confirmation since it's money movement)
- A small "Wallet balance" dashboard widget on the admin index (via a custom `AdminSite` or `django-admin-tools`)

---

## 10. Configuration & Secrets

```python
# settings/base.py
MOOLRE = {
    "ENVIRONMENT": env("MOOLRE_ENV", default="sandbox"),  # sandbox | live
    "BASE_URL": {
        "sandbox": "https://sandbox.moolre.com",
        "live": "https://api.moolre.com",
    },
    "API_USER": env("MOOLRE_API_USER"),
    "API_KEY": env("MOOLRE_API_KEY", default=None),        # not required in sandbox
    "API_PUBKEY": env("MOOLRE_API_PUBKEY", default=None),
    "API_VASKEY": env("MOOLRE_API_VASKEY"),
    "DEFAULT_CURRENCY": "GHS",
    "TIMEOUT": 15,
    "MAX_RETRIES": 3,
}
```

- Never commit keys; use `django-environ`/`.env` + a secrets manager in prod
- Separate sandbox vs. live credentials per Django settings module (`dev.py` forces `sandbox`)
- Store each wallet's `secret` (returned on creation) encrypted at rest (e.g. `django-fernet-fields` or `django-cryptography`)

---

## 11. Reliability & Correctness Rules (from Moolre's own guides)

- **Idempotency**: always generate a UUID/ULID as `externalref`/`ref` client-side *before* calling Moolre, store it, and reuse it on retry — never regenerate on retry (`TP13` duplicate-ref errors are Moolre telling you it already got this request)
- **Safe retries**: only retry on network timeouts / 5xx; a `400` with a validation error should not be retried blindly
- **Status codes**: centralize Moolre's `code` values (`WC02`, `SS01`, `TP14`, `AIN01`, etc.) in `moolre_client/codes.py` as an enum, map to internal statuses in one place
- **OTP flows**: `initiate_payment`/`internal_transfer` can return `TP14` (OTP required) — model this as a `PaymentRequest.status = "otp_pending"` and support a follow-up "confirm with OTP" call
- Go-live checklist item: swap sandbox keys → live keys, re-point `callback` URLs to production domain, confirm webhook endpoint is publicly reachable over HTTPS

---

## 12. Testing Strategy

- Unit test `moolre_client` against **recorded sandbox fixtures** (VCR.py / `responses` library) — no live network calls in CI
- Integration test suite runnable manually against real Moolre **sandbox** (`X-API-USER` only)
- Webhook tests: POST sample payloads from the docs (`Payment Webhook` example) at `/webhooks/moolre/payments/` and assert idempotent processing (send twice, assert one status update)
- Contract tests: snapshot Moolre's documented example responses (from `llms-full.txt`) as fixtures so client parsing breaks loudly if the API shape changes

---

## 13. Build Order (Milestones)

1. **Scaffolding**: Django project, settings, `moolre_client` with `accounts` + `misc` endpoints only, admin skeleton
2. **Wallets**: create/update/status/list-transactions, admin views, balance sync task
3. **Collections**: USSD push payment + status polling + webhook receiver (highest priority — this is core revenue path)
4. **Payment links & virtual accounts**: for e-commerce / recurring collection use cases
5. **Disbursements**: name validation → transfer → status, with an approval step before money moves
6. **Messaging**: SMS send/status, sender ID management, WhatsApp templates/send/status
7. **REST API layer**: build out the full DRF surface in Section 8 (wallets, payments, transfers, messaging, reference data), OpenAPI schema, idempotency handling, permission tiers
8. **Hardening**: encrypted secrets at rest, rate limiting on transfer/messaging endpoints, audit logging on money-moving actions
9. **Go-live**: switch to live keys, load-test webhook endpoint, enable monitoring/alerts on failed transfers and webhook processing errors

> **v2 backlog**: Celery-based background jobs (Section 7) — automatic polling/reconciliation instead of on-demand status checks.

---

## 14. Suggested Tech Stack

- Django 5.x + Django REST Framework + `drf-spectacular` for OpenAPI schema
- `httpx` (or `requests`) + `tenacity` for retries/backoff in `moolre_client`
- PostgreSQL (JSONField for raw payloads, unique constraints for idempotency keys)
- `django-environ` for config, `django-cryptography`/`django-fernet-fields` for encrypted secrets
- `responses` or `VCR.py` for API mocking in tests
- Sentry (or similar) for alerting on webhook failures / failed transfers
- **v2**: Celery + Redis for polling/reconciliation/async webhook follow-up (see Section 7)
