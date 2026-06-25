import hashlib
import hmac
import logging
import secrets
import time

from ..env import SECRET_KEY, ENVIRONMENT, SESSION_LIFETIME

logger = logging.getLogger(__name__)

# Minimum acceptable secret length. 32 url-safe chars is ~192 bits of entropy,
# matching the `secrets.token_urlsafe(32)` we tell operators to generate.
_MIN_SECRET_LEN = 32


def _load_key() -> bytes:
    """Resolve the HMAC key, failing closed in production.

    A weak or empty key makes session cookies forgeable, and identity here *is*
    the PGP fingerprint, so a forgeable cookie means full impersonation. In
    production we refuse to start. In development/test we fall back to an
    ephemeral random key so things still run -- crucially that key is secret and
    random, so cookies are still unforgeable; they just don't survive a restart.
    """
    key = (SECRET_KEY or "").strip()
    if len(key) >= _MIN_SECRET_LEN:
        return key.encode()

    if ENVIRONMENT == "production":
        raise RuntimeError(
            f"SECRET_KEY is unset or shorter than {_MIN_SECRET_LEN} characters. "
            "Refusing to start in production with forgeable session cookies. "
            "Generate one with: "
            'python -c "import secrets; print(secrets.token_urlsafe(32))"'
        )

    logger.warning(
        "SECRET_KEY is unset or weak; using an ephemeral random key. Sessions "
        "will not survive a restart. Set a strong SECRET_KEY before deploying."
    )
    return secrets.token_bytes(32)


_KEY = _load_key()


def _signature(value: str) -> str:
    return hmac.new(_KEY, value.encode(), hashlib.sha256).hexdigest()


def sign_user_id(user_id: str) -> str:
    """Return a signed cookie value carrying the user id and its issue time.

    Format: ``user_id.issued_at.hmac(user_id.issued_at)``. Binding the issue
    time into the signed payload lets :func:`unsign_user_id` reject sessions
    older than ``SESSION_LIFETIME`` without trusting the (unsigned) cookie Max-Age.
    """
    payload = f"{user_id}.{int(time.time())}"
    return f"{payload}.{_signature(payload)}"


def unsign_user_id(token: str | None) -> str | None:
    """Return the user id iff ``token`` is validly signed and not expired.

    This is what makes identity unforgeable: the user id is the public PGP
    fingerprint, so without verifying the HMAC anyone could impersonate anyone
    by simply setting the cookie. Expired or future-dated tokens are rejected.
    """
    if not token:
        return None
    payload, _, signature = token.rpartition(".")
    if not payload or not signature:
        return None
    if not hmac.compare_digest(signature, _signature(payload)):
        return None

    user_id, _, issued_at = payload.rpartition(".")
    if not user_id or not issued_at:
        return None
    try:
        age = int(time.time()) - int(issued_at)
    except ValueError:
        return None
    # Reject expired sessions and ones dated in the future (clock games).
    if age < 0 or age > SESSION_LIFETIME:
        return None
    return user_id
