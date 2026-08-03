"""
Payment / collection endpoints — PLACEHOLDER.

Scope (plan Section 2, "Payment" row group). Build order (plan Section 13):
Milestone 3 = USSD push + status + webhook (core revenue path, highest
priority); Milestone 4 = payment links & virtual accounts. Not implemented
yet — this file exists so the package structure matches the plan from the
start.

Endpoints to wrap here:
    POST /open/transact/payment          -> initiate_ussd() (real code TR099,
                                             OTP path TP14, dup-ref TP13 —
                                             see codes.py, confirmed against
                                             docs.moolre.com/ai/initiate-payment)
    POST /open/account/create (type=2)   -> create_payment_id()
    POST /open/account/create (type=9)   -> create_virtual_account()
    POST /embed/link                      -> create_payment_link()
    POST /open/transact/status            -> status()
"""

from __future__ import annotations


class PaymentsEndpoints:
    def __init__(self, client):
        self._client = client

    # TODO(milestone-3/4): initiate_ussd(), create_payment_id(),
    # create_virtual_account(), create_payment_link(), status()
