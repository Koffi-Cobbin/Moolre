"""
SMS endpoints — PLACEHOLDER.

Scope (plan Section 2, "SMS" row group). Build order: Milestone 6
("Messaging"). Not implemented yet — this file exists so the package
structure matches the plan from the start.

Endpoints to wrap here:
    POST/GET /open/sms/send   -> send()
    POST /open/sms/status     -> status() / account_status() / sender IDs (type-switched: 1,2,5,6,7)
    POST /open/sms/query      -> create_sender_id()
"""

from __future__ import annotations


class SmsEndpoints:
    def __init__(self, client):
        self._client = client

    # TODO(milestone-6): send(), status(), account_status(), sender ID mgmt
