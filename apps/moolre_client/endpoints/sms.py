"""
SMS endpoints (plan Section 2, "SMS" row group).

All SMS endpoints share the physical URL /open/sms/status, disambiguated
by `type` (per docs.moolre.com/ai/*, confirmed during scaffolding):
    type=1 -- sender ID status      type=5 -- SMS delivery status
    type=2 -- account/credit status  type=6 -- approve/reject sender IDs
    type=7 -- list sender IDs
/open/sms/send and /open/sms/query are separate physical endpoints.

All SMS endpoints require X-API-VASKEY (confirmed on every page).
"""

from __future__ import annotations

from typing import Any


class SmsEndpoints:
    def __init__(self, client):
        self._client = client

    def send(self, *, senderid: str, messages: list[dict]) -> dict:
        """POST /open/sms/send -- bulk or single SMS.

        `messages`: list of {"recipient": str, "message": str, "ref": str (optional)}.
        Source: docs.moolre.com/ai/send-sms.html -- success SMS01,
        unapproved sender ID ASMS07.
        """
        payload: dict[str, Any] = {"type": 1, "senderid": senderid, "messages": messages}
        return self._client.request(
            "POST", "/open/sms/send", key_types=("API_VASKEY",), json=payload
        )

    def status(self, *, refs: list[str]) -> dict:
        """POST /open/sms/status (type=5) -- delivery status for message refs.

        Source: docs.moolre.com/ai/sms-status.html -- success ASMQ10.
        """
        payload = {"type": 5, "ref": refs}
        return self._client.request(
            "POST", "/open/sms/status", key_types=("API_VASKEY",), json=payload
        )

    def account_status(self) -> dict:
        """POST /open/sms/status (type=2) -- SMS credit balance.

        Source: docs.moolre.com/ai/sms-account-status.html -- success ASMQ03.
        """
        payload = {"type": 2}
        return self._client.request(
            "POST", "/open/sms/status", key_types=("API_VASKEY",), json=payload
        )

    def create_sender_id(self, *, senderids: list[dict]) -> dict:
        """POST /open/sms/query (type=3) -- request new Sender ID(s).

        `senderids`: list of {"senderid": str, "approve": bool (optional)}.
        Source: docs.moolre.com/ai/create-sender-id.html -- success ASMQ12,
        permission denied ASMQ09.
        """
        payload = {"type": 3, "senderids": senderids}
        return self._client.request(
            "POST", "/open/sms/query", key_types=("API_VASKEY",), json=payload
        )

    def sender_id_status(self, *, senderid: str) -> dict:
        """POST /open/sms/status (type=1) -- check one Sender ID's approval status.

        Source: docs.moolre.com/ai/sender-id-status.html -- success ASMQ01
        (approval: "Approved" | "Pending" | "Rejected").
        """
        payload = {"type": 1, "senderid": senderid}
        return self._client.request(
            "POST", "/open/sms/status", key_types=("API_VASKEY",), json=payload
        )

    def list_sender_ids(self) -> dict:
        """POST /open/sms/status (type=7) -- list all registered Sender IDs.

        Source: docs.moolre.com/ai/list-sender-ids.html -- success ASMQ08.
        """
        payload = {"type": 7}
        return self._client.request(
            "POST", "/open/sms/status", key_types=("API_VASKEY",), json=payload
        )

    def approve_sender_ids(self, *, senderids: list[dict]) -> dict:
        """POST /open/sms/status (type=6) -- approve/reject Sender ID(s).

        `senderids`: list of {"senderid": str, "approve": int} where
        approve is 0=Pending, 1=Approved, 2=Rejected.
        Source: docs.moolre.com/ai/approve-sender-id.html -- success
        ASMQ07, permission denied ASMQ09.
        """
        payload = {"type": 6, "senderids": senderids}
        return self._client.request(
            "POST", "/open/sms/status", key_types=("API_VASKEY",), json=payload
        )
