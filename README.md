# Moolre Payments & Messaging Platform — Django Project

This is the Milestone 1 scaffold from `moolre-django-plan.md`
("Scaffolding: Django project, settings, `moolre_client` with `accounts` +
`misc` endpoints only, admin skeleton") plus Milestones 2 through 6
(Wallets, Collections, Payment links & virtual accounts, Disbursements,
Messaging), and the remaining gap from Milestone 7 (Reference/misc data
endpoints, rounding out every table in plan Section 8).

## What's implemented

- **`apps/moolre_client/`** — Django-free Python SDK for the Moolre API.
  - `client.py`: auth headers (`X-API-USER` always; `X-API-KEY` /
    `X-API-PUBKEY` / `X-API-VASKEY` per endpoint type — both `API_KEY` and
    `API_PUBKEY` are optional in sandbox per plan Section 2), retry-on-5xx/
    timeout via `tenacity`, error mapping into `exceptions.py`.
  - `codes.py`: real Moolre response codes (`WC02`, `SW01`, `ST08`, `SD01`,
    `AIN04`, `TP13`, `TP14`, `TR099`, `P01`, `SS01`, `POS09`, `INP02`,
    `AD14`, `AD19`, `AD32`, `AVD01`, `AVD02`, `OBGH01`, `SMS01`, `ASMS07`,
    `AIN01`, `ASMQ01/03/07/08/09/10/12`, `WAS200`, `WAS401`) — pulled from
    `docs.moolre.com/ai/*` during scaffolding, not guessed.
  - `endpoints/{accounts,misc,payments,transfers,sms,whatsapp}.py` — all
    fully implemented (every endpoint group from the plan's Section 2 API
    surface now has a real wrapper). Note: transfer channel codes
    (`1=MTN, 6=Telecel, 7=AT, 2=Bank`) are *different* from USSD collection
    channel codes (`13=MTN, 6=Telecel, 7=AT`) — confirmed from the docs,
    not assumed to be the same enum. Also confirmed all 7 SMS
    status/management calls share one physical URL (`/open/sms/status`)
    disambiguated only by `type` — documented in the module so nobody
    reads it as 7 separate endpoints.
  - `signing.py` — webhook verification. Moolre's documented webhook
    payload has no signature header, so this implements the plan's
    "verify, don't trust" fallback (re-check status) instead of HMAC —
    confirmed against Moolre's own webhooks-and-callbacks guide.
- **`apps/wallets/`** — full vertical slice: `Wallet` / `SettlementConfig`
  models (wallet `secret` encrypted at rest), `services.py`
  (`create_wallet`, `update_wallet`, `sync_balance`, `list_transactions`),
  and an admin with a "Refresh balance" action.
- **`apps/payments/`** — full vertical slice covering Milestones 3-4:
  `PaymentRequest` / `WebhookEvent` (USSD collections) plus `PaymentLink`,
  `VirtualAccount`, `PaymentIdTerminal` (Milestone 4). `services.py` has
  `initiate_ussd_payment`, `confirm_otp`, `check_payment_status`,
  `create_payment_link`, `create_virtual_account`,
  `create_payment_id_terminal`. Django signals (`payment_completed`,
  `payment_failed`) fire idempotently (only on an actual status
  transition, so webhook redelivery doesn't double-fire side effects).
  The webhook receiver at `/webhooks/moolre/payments/` implements the
  full flow from plan Section 6 (persist → validate → verify-via-status
  → update idempotently → 200 fast). Admin has "Re-check status" /
  "Resend webhook processing" actions.
- **`apps/transfers/`** — full vertical slice implementing the plan's
  maker-checker requirement (Section 8: "separate permission class,
  optional maker-checker/approval step before the transfer is actually
  sent to Moolre, and full audit logging of who triggered it"):
  `create_transfer()`/`create_internal_transfer()` only ever write a local
  `PENDING_APPROVAL` row — Moolre is never contacted. The *only* function
  that sends money is `approve_and_send_transfer()`, which requires an
  approving user. `NameValidationLog` + `Transfer` models, `validate_name`,
  `confirm_transfer_otp`, `check_transfer_status`, `reject_transfer`
  services, `transfer_completed`/`transfer_failed` signals (idempotent on
  redelivery, same pattern as payments), and an admin with a guarded
  "Retry transfer" action that renders an explicit confirmation page
  before resending (plan Section 9).
- **`apps/messaging/`** — full vertical slice: `SenderId`, `SmsMessage`,
  `WhatsAppTemplate`, `WhatsAppMessage` models (no `wallet` FK — Moolre's
  `X-API-VASKEY` is account-level, not per-wallet, matching the plan's own
  model list for this domain). `services.py` covers send (single + bulk
  SMS), status checks, SMS credit balance, sender ID request/list/refresh/
  approve, and WhatsApp template sync/send/status. Admin has sync/refresh/
  approve/reject actions.
- **`apps/api/`** — DRF `WalletViewSet`, `PaymentRequestViewSet`,
  `PaymentLinkViewSet`, `VirtualAccountViewSet`, `PaymentIdTerminalViewSet`,
  `TransferViewSet`, `NameValidationViewSet`, `SmsMessageViewSet`,
  `SenderIdViewSet`, `WhatsAppTemplateViewSet`, `WhatsAppMessageViewSet` —
  every domain from the plan's Section 8 API tables now has a working
  endpoint, wrapped in the `{success, code, message, data}` envelope.
  `Transfer` and `SenderId` approval actions require staff (`IsAdminUser`),
  enforcing the maker-checker/approval split at the permission layer.
  Plus `BanksReferenceView` / `ChannelsReferenceView` (plain `APIView`s,
  not model-backed) completing the plan's "Reference / misc" table —
  **caveat**: `docs.moolre.com/ai/miscellaneous-data.html` only documents
  `data=banks` as a concrete example; the exact string for mobile money
  channels isn't enumerated anywhere in the docs. Rather than fabricate
  one, `ChannelsReferenceView` defaults to `"channels"` as a best guess
  but accepts `?data=` to override — confirm the real value against
  sandbox before relying on it.
- **`apps/ledger/`** — the plan's one *optional*, unscheduled app (Section
  3: "internal double-entry bookkeeping / reconciliation"); still a valid,
  migratable Django app with no models, since it's out of the v1 build
  order entirely (plan Section 13).
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
- Milestone 4: `create_payment_link()`, `create_virtual_account()`,
  `create_payment_id_terminal()` against a mocked Moolre layer (asserting
  `API_PUBKEY` auth is used, matching the real docs — not `API_KEY`), plus
  their three DRF endpoints end-to-end (`/api/payments/links/`,
  `/api/payments/virtual-accounts/`, `/api/payments/payment-ids/`)
- Milestone 5: `create_transfer()` asserted to make **zero** Moolre calls
  (writes `PENDING_APPROVAL` only); `approve_and_send_transfer()` actually
  sends and asserted to reject double-approval; internal-transfer OTP
  flow (`TP14` → `confirm_transfer_otp()` → accepted); `reject_transfer()`
  blocks a subsequent approval attempt; the DRF permission split tested
  directly — a regular authenticated user gets `403` on `/approve/`, staff
  gets `200` and the transfer actually sends (mocked); the guarded admin
  "Retry transfer" action's intermediate confirmation page was rendered
  and checked for content, not just imported

- Milestone 6: SMS send/status/account-balance and WhatsApp templates/
  send/status against a mocked layer (asserting `API_VASKEY` auth on every
  call); sender ID request → approve flow; a real route-ordering bug was
  caught and fixed here (`/api/sms/sender-ids/` was initially getting
  swallowed by `SmsMessageViewSet`'s `<ref>` detail regex — same class of
  issue as the `transfers/validate-name` fix in Milestone 5, now fixed the
  same way: register the more specific prefix first); DRF permission split
  tested directly on `/api/sms/sender-ids/{id}/approve/` (403 regular
  user, 200 staff)

- Milestone 7: reference-data endpoints against a mocked layer (asserting
  `API_KEY` auth, per the plan's own header table); confirmed the OpenAPI
  schema (`/api/schema/`) generates cleanly with zero drf-spectacular
  warnings across all 12 viewsets/views, and that the Swagger UI
  (`/api/schema/docs/`) actually renders — not just that the URLconf
  resolves

## Next up (per the plan's build order, Section 13)

8. Hardening: rate limiting on transfer/messaging endpoints, more audit
   logging on money-moving actions (partially done via `requested_by`/
   `approved_by` on `Transfer`)
9. Go-live: switch to live keys, load-test the webhook endpoint, monitoring/
   alerts on failed transfers and webhook processing errors

Every table in the plan's REST API layer (Section 8) is now backed by a
real endpoint, and all 6 v1 milestones plus the REST API rollout
(Milestone 7) are implemented. What's left is hardening and go-live —
config/process work rather than new application code.
