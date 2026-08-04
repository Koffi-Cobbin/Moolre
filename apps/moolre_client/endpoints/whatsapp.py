"""
WhatsApp endpoints (plan Section 2, "WhatsApp" row group).

All confirmed against docs.moolre.com/ai/whatsapp-{get-templates,
send-message,message-status}.html -- all require X-API-VASKEY, all share
the WAS200 generic success code (WAS401 = insufficient WhatsApp balance).
"""

from __future__ import annotations


class WhatsAppEndpoints:
    def __init__(self, client):
        self._client = client

    def templates(self) -> dict:
        """GET /open/whatsapp/template -- fetch approved/pending/rejected templates.

        Source: docs.moolre.com/ai/whatsapp-get-templates.html.
        """
        return self._client.request(
            "GET", "/open/whatsapp/template", key_types=("API_VASKEY",)
        )

    def send(self, *, template_name: str, language: str, messages: list[dict]) -> dict:
        """POST /open/whatsapp/send -- batch templated send.

        `messages`: list of {"recipient": str, "ref": str (optional, needed
        to check status later), "placeholders": dict/list (optional)}.
        Source: docs.moolre.com/ai/whatsapp-send-message.html -- WAS200
        success (or partial-success with a duplicate-ref warning),
        WAS401 insufficient balance.
        """
        payload = {
            "template_name": template_name,
            "language": language,
            "messages": messages,
        }
        return self._client.request(
            "POST", "/open/whatsapp/send", key_types=("API_VASKEY",), json=payload
        )

    def status(self, *, refs: list[str]) -> dict:
        """POST /open/whatsapp/status -- batch delivery status check.

        Source: docs.moolre.com/ai/whatsapp-message-status.html -- WAS200,
        `data[].status` in {"accepted", "read", ...}.
        """
        payload = {"ref": refs}
        return self._client.request(
            "POST", "/open/whatsapp/status", key_types=("API_VASKEY",), json=payload
        )
