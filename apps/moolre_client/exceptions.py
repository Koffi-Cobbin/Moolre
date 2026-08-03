"""
Exception hierarchy for moolre_client.

Kept separate from Django's exceptions on purpose (plan Section 3: the
client has zero Django dependencies) so it can be reused outside Django.
"""


class MoolreError(Exception):
    """Base class for all moolre_client errors."""


class MoolreNetworkError(MoolreError):
    """Raised on connection errors / timeouts talking to the Moolre API.

    Safe to retry (plan Section 11: "only retry on network timeouts / 5xx").
    """


class MoolreAuthError(MoolreError):
    """Raised when required auth headers are missing or Moolre rejects credentials."""


class MoolreValidationError(MoolreError):
    """Raised on 4xx responses / malformed request payloads.

    Per plan Section 11: "a 400 with a validation error should not be
    retried blindly" — callers should treat this as terminal, not transient.
    """

    def __init__(self, message, *, code=None, raw_response=None):
        super().__init__(message)
        self.code = code
        self.raw_response = raw_response


class MoolreAPIError(MoolreError):
    """Raised when Moolre returns a non-success `status`/`code` in an otherwise
    well-formed (HTTP 200) response body.

    Attributes mirror the fields documented for Moolre's response envelope
    and the codes centralized in `codes.py` (plan Section 11).
    """

    def __init__(self, message, *, code=None, raw_response=None):
        super().__init__(message)
        self.code = code
        self.raw_response = raw_response

    def __str__(self):
        base = super().__str__()
        if self.code:
            return f"[{self.code}] {base}"
        return base
