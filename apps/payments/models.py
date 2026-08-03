"""
Payments (collections) domain — models PLACEHOLDER.

Build order (plan Section 13): Milestone 3 = USSD push payment + status +
webhook receiver (highest priority, core revenue path). Milestone 4 =
payment links & virtual accounts.

Planned models (plan Section 4, "payments (collections)"):

    PaymentRequest(wallet FK, channel, amount, currency, payer_msisdn,
                   externalref UNIQUE, transactionid, status, otp_required,
                   session_id, created_at, updated_at)
    PaymentLink(wallet FK, externalref UNIQUE, amount, currency,
                authorization_url, reusable, expires_at, metadata JSON, status)
    VirtualAccount(wallet FK, accountno, accountname, bankname, uref UNIQUE,
                   holder_first_name, holder_last_name, phone, email)
    PaymentIdTerminal(wallet FK, paymentid, holder_name, phone, externalref)
    WebhookEvent(raw_payload JSON, signature, verified BOOL, processed BOOL,
                 received_at) — append-only audit log of every inbound callback

Not implemented yet — this file exists (with no models) so `apps.payments`
is a valid, migratable Django app from the start of scaffolding.
"""
