import hashlib
import hmac
import logging

from ..env import SECRET_KEY

logger = logging.getLogger(__name__)

_KEY = (SECRET_KEY or "").encode()

if not _KEY:
    logger.warning(
        "SECRET_KEY is not set; session cookies are forgeable. "
        "Set SECRET_KEY in .env before deploying."
    )


def _signature(value: str) -> str:
    return hmac.new(_KEY, value.encode(), hashlib.sha256).hexdigest()


def sign_user_id(user_id: str) -> str:
    """Return ``user_id`` with an appended HMAC tag, for use as a cookie value."""
    return f"{user_id}.{_signature(user_id)}"


def unsign_user_id(token: str | None) -> str | None:
    """Return the user id iff ``token`` carries a valid signature, else None.

    This is what makes identity unforgeable: the user id is the public PGP
    fingerprint, so without verifying the HMAC anyone could impersonate anyone
    by simply setting the cookie.
    """
    if not token or "." not in token:
        return None
    value, _, signature = token.rpartition(".")
    if not value or not signature:
        return None
    if hmac.compare_digest(signature, _signature(value)):
        return value
    return None
