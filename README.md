# Moolre Payments & Messaging Platform — Django Project

This is the Milestone 1 scaffold from `moolre-django-plan.md`
("Scaffolding: Django project, settings, `moolre_client` with `accounts` +
`misc` endpoints only, admin skeleton") plus Milestone 2 ("Wallets") and
Milestone 3 ("Collections: USSD push payment + status polling + webhook
receiver — highest priority, core revenue path").

## What's implemented

- **`apps/moolre_client/`** — Django-free Python SDK for the Moolre API.
  - `client.py`: auth headers (`X-API-USER` always; `X-API-KEY` /
    `X-API-PUBKEY` / `X-API-VASKEY` per endpoint type — both `API_KEY` and
    `API_PUBKEY` are optional in sandbox per plan Section 2), retry-on-5xx/
    timeout via `tenacity`, error mapping into `exceptions.py`.
  - `codes.py`: real Moolre response codes (`WC02`, `SW01`, `ST08`, `SD01`,
    `AIN04`, `TP13`, `TP14`, `TR099`, `P01`, `SS01`) — pulled from
    `docs.moolre.com/ai/*` during scaffolding, not guessed.
  - `endpoints/accounts.py`, `endpoints/misc.py`, `endpoints/payments.py`
    (`initiate_ussd()`, `status()`) — fully implemented.
  - `endpoints/{transfers,sms,whatsapp}.py` — documented placeholders for
    Milestones 4–6.
  - `signing.py` — webhook verification. Moolre's documented webhook
    payload has no signature header, so this implements the plan's
    "verify, don't trust" fallback (re-check status) instead of HMAC —
    confirmed against Moolre's own webhooks-and-callbacks guide.
- **`apps/wallets/`** — full vertical slice: `Wallet` / `SettlementConfig`
  models (wallet `secret` encrypted at rest), `services.py`
  (`create_wallet`, `update_wallet`, `sync_balance`, `list_transactions`),
  and an admin with a "Refresh balance" action.
- **`apps/payments/`** — full vertical slice: `PaymentRequest` / `WebhookEvent`
  models, `services.py` (`initiate_ussd_payment`, `confirm_otp`,
  `check_payment_status`), Django signals (`payment_completed`,
  `payment_failed`) fired idempotently (only on an actual status
  transition, so webhook redelivery doesn't double-fire side effects),
  a webhook receiver at `/webhooks/moolre/payments/` implementing the
  full flow from plan Section 6 (persist → validate → verify-via-status
  → update idempotently → 200 fast), and an admin with "Re-check status"
  / "Resend webhook processing" actions.
- **`apps/api/`** — DRF `WalletViewSet` + `PaymentRequestViewSet` mirroring
  the plan's Wallets and Collections tables (list/create/retrieve +
  `/balance/`, `/transactions/`, `/confirm-otp/`, `/status/`), wrapped in
  the `{success, code, message, data}` envelope from Section 8, with
  auto-generated `externalref`/Idempotency-Key handling on create.
- **`apps/{transfers,messaging,ledger}/`** — valid, migratable Django apps
  with no models yet; each `models.py` documents exactly what lands there
  and in which milestone, per the plan's build order.
- `config/` — settings (`dev.py` forces sandbox, per the plan), root
  URLconf, WSGI/ASGI, and a `celery.py` placeholder (Celery itself is
  v2 scope per plan Section 7).

## One real-world fix worth knowing about

The plan's suggested `django-cryptography` package (v1.1 on PyPI) is
abandoned and **breaks on Django 5+** (it imports `django.utils.baseconv`,
which Django removed in 5.0 —
[confirmed upstream](https://github.com/georgemarshall/django-cryptography/issues/115)).
`requirements.txt` installs the maintained fork, **`django-cryptography-5`**,
instead — same import path (`from django_cryptography.fields import
encrypt`), no code changes needed, just a different PyPI package name.

## Running it

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in MOOLRE_API_USER / MOOLRE_API_VASKEY at minimum for sandbox
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Then:
- Admin: `http://localhost:8000/admin/`
- API: `http://localhost:8000/api/wallets/`
- OpenAPI schema/docs: `http://localhost:8000/api/schema/docs/`

Verified during scaffolding: `manage.py check` passes, `makemigrations` +
`migrate` succeed against SQLite, root URLconf resolves, and — beyond
static checks — the actual request flows were exercised with the Moolre
HTTP layer mocked:
- USSD initiate → success (`TR099` → `pending` → webhook → `success`,
  signal fires exactly once even across 3 redelivered webhooks)
- USSD initiate → OTP required (`TP14` → `otp_pending`) → `confirm_otp()`
  → accepted
- Duplicate `externalref` (`TP13`) → treated as an idempotent retry ack,
  not a hard failure
- Webhook edge cases: malformed JSON (400, still logged), missing fields
  (400), unknown `externalref` (200, not marked processed)
- The DRF API end-to-end as an authenticated user: `POST /api/payments/ussd/`
  (with auto-generated `externalref`) → `GET /api/payments/ussd/`

## Next up (per the plan's build order, Section 13)

4. Payment links & virtual accounts
5. Disbursements (`apps/transfers/`)
6. Messaging: SMS + WhatsApp (`apps/messaging/`)
7. Round out the REST API layer for the above
8. Hardening, then go-live
