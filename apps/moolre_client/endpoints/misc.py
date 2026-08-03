"""
Reference / miscellaneous data endpoint (plan Section 2, "Misc" row).

Source: docs.moolre.com/ai/miscellaneous-data.md
    GET /open/transact/data?country=<code>&data=<type>  -> SD01 on success
"""

from __future__ import annotations


class MiscEndpoints:
    def __init__(self, client):
        self._client = client

    def reference_data(self, *, country: str, data: str) -> dict:
        """GET /open/transact/data — banks, mobile money channels, etc.

        Example: `reference_data(country="gha", data="banks")` mirrors the
        REST API's `/api/reference/banks/?country=gha` (plan Section 8).
        """
        params = {"country": country, "data": data}
        return self._client.request(
            "GET", "/open/transact/data", key_types=("API_KEY",), params=params
        )
