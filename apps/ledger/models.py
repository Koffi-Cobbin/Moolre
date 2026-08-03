"""
Ledger — optional internal double-entry bookkeeping / reconciliation
(plan Section 3: "Optional: internal double-entry bookkeeping /
reconciliation").

Not scheduled in the v1 build order (plan Section 13) at all — the closest
touchpoint is the v2-backlog `reconcile_transactions` task (plan Section 7),
which would cross-check this ledger against `wallets.list_transactions()`.
No models defined yet; add them here if/when reconciliation becomes a
priority.
"""
