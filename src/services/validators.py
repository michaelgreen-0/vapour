import re

# A PGP v4 fingerprint as pgpy renders it (str(key.fingerprint)): exactly 40
# uppercase hex characters, no spaces. User identity is the fingerprint, so any
# routing target must look like one -- this keeps arbitrary text out of the
# connection map, logs, and message routing.
_FINGERPRINT_RE = re.compile(r"\A[0-9A-F]{40}\Z")


def is_valid_fingerprint(value) -> bool:
    """Return True iff ``value`` is a syntactically valid PGP fingerprint."""
    return isinstance(value, str) and _FINGERPRINT_RE.match(value) is not None
