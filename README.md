# Moolre Payments & Messaging Platform — Django Project

This is the Milestone 1 scaffold from `moolre-django-plan.md`
("Scaffolding: Django project, settings, `moolre_client` with `accounts` +
`misc` endpoints only, admin skeleton") plus a working slice of Milestone 2
("Wallets: create/update/status/list-transactions, admin views").

## What's implemented

- **`apps/moolre_client/`** — Django-free Python SDK for the Moolre API.
  - `client.py`: auth headers (`X-API-USER` always; `X-API-KEY` /
    `X-API-PUBKEY` / `X-API-VASKEY` per endpoint type), retry-on-5xx/timeout
    via `tenacity`, error mapping into `exceptions.py`.
  - `codes.py`: real Moolre response codes (`WC02`, `SW01`, `ST08`, `SD01`,
    `AIN04`, `TP13`, `TP14`, `TR099`, `P01`) — pulled from
    `docs.moolre.com/ai/*` during scaffolding, not guessed.
  - `endpoints/accounts.py`, `endpoints/misc.py` — fully implemented.
  - `endpoints/{transfers,payments,sms,whatsapp}.py` — documented
    placeholders for Milestones 3–6.
  - `signing.py` — webhook verification. Moolre's documented webhook
    payload has no signature header, so this implements the plan's
    "verify, don't trust" fallback (re-check status) instead of HMAC.
- **`apps/wallets/`** — full vertical slice: `Wallet` / `SettlementConfig`
  models (wallet `secret` encrypted at rest), `services.py`
  (`create_wallet`, `update_wallet`, `sync_balance`, `list_transactions`),
  and an admin with a "Refresh balance" action.
- **`apps/api/`** — DRF `WalletViewSet` mirroring the plan's Wallets table
  (list/create/retrieve/patch + `/balance/` + `/transactions/`), wrapped in
  the `{success, code, message, data}` envelope described in Section 8.
- **`apps/{payments,transfers,messaging,ledger}/`** — valid, migratable
  Django apps with no models yet; each `models.py` documents exactly what
  lands there and in which milestone, per the plan's build order.
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
`migrate` succeed against SQLite, root URLconf resolves, and the client's
sandbox-vs-live auth header logic was smoke-tested directly.

## Next up (per the plan's build order, Section 13)

3. Collections: USSD push payment + status + webhook receiver (core revenue
   path — `apps/payments/webhooks.py` currently just returns 501)
4. Payment links & virtual accounts
5. Disbursements (`apps/transfers/`)
6. Messaging: SMS + WhatsApp (`apps/messaging/`)
7. Round out the REST API layer for the above
8. Hardening, then go-live
