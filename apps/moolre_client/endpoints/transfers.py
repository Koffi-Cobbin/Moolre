"""
Transfer / disbursement endpoints — PLACEHOLDER.

Scope (plan Section 2, "Transfer" row group): validate, transfer, status,
internal. Build order (plan Section 13) puts this at Milestone 5
("Disbursements"), after Wallets and Collections. Not implemented yet —
this file exists so the package structure matches the plan from the start.

Endpoints to wrap here when this milestone starts:
    POST /open/transact/validate  -> validate_name()
    POST /open/transact/transfer  -> transfer()
    POST /open/transact/status    -> status()
    POST /open/transact/internal  -> internal_transfer()
"""

from __future__ import annotations


class TransfersEndpoints:
    def __init__(self, client):
        self._client = client

    # TODO(milestone-5): validate_name(), transfer(), status(), internal_transfer()
