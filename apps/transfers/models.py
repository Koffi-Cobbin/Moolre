"""
Transfers (disbursements) domain — models PLACEHOLDER.

Build order (plan Section 13): Milestone 5 ("Disbursements": name
validation -> transfer -> status, with an approval step before money moves).

Planned models (plan Section 4, "transfers (disbursements)"):

    NameValidationLog(receiver, channel, resolved_name, status, created_at)
    Transfer(wallet FK, channel, currency, amount, receiver, sublistid,
             externalref UNIQUE, reference, transactionid, thirdpartyref,
             status, fee, network_fee, created_at, updated_at)

Not implemented yet — this file exists (with no models) so `apps.transfers`
is a valid, migratable Django app from the start of scaffolding.
"""
