"""
moolre_client — a thin, Django-free Python SDK for the Moolre API.

See plan Section 2 (API surface) and Section 3 ("Design principle: moolre_client
has zero Django dependencies"). Django apps call into this via their
`services.py` modules; this package never imports `django`.
"""

from .client import MoolreClient  # noqa: F401
from .exceptions import (  # noqa: F401
    MoolreAPIError,
    MoolreAuthError,
    MoolreError,
    MoolreNetworkError,
    MoolreValidationError,
)

__all__ = [
    "MoolreClient",
    "MoolreError",
    "MoolreAPIError",
    "MoolreAuthError",
    "MoolreNetworkError",
    "MoolreValidationError",
]
