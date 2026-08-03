"""
WhatsApp endpoints — PLACEHOLDER.

Scope (plan Section 2, "WhatsApp" row group). Build order: Milestone 6
("Messaging"). Not implemented yet — this file exists so the package
structure matches the plan from the start.

Endpoints to wrap here:
    GET  /open/whatsapp/template -> templates()
    POST /open/whatsapp/send     -> send()
    POST /open/whatsapp/status   -> status()
"""

from __future__ import annotations


class WhatsAppEndpoints:
    def __init__(self, client):
        self._client = client

    # TODO(milestone-6): templates(), send(), status()
