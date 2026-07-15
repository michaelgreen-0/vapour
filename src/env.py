import os
from dotenv import load_dotenv

load_dotenv()

CHALLENGE_LIFETIME = os.getenv("CHALLENGE_LIFETIME")
REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = os.getenv("REDIS_PORT")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
SECRET_KEY = os.getenv("SECRET_KEY")

# Deployment environment. "production" makes config validation strict (e.g.
# refusing to start without a strong SECRET_KEY). Anything else is treated as
# development/test, where weak-config fallbacks are allowed for convenience.
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").strip().lower()

# How long a session cookie stays valid, in seconds. Default 12h. Kept short so
# a leaked cookie expires on its own even without server-side revocation.
SESSION_LIFETIME = int(os.getenv("SESSION_LIFETIME", str(12 * 60 * 60)))

# Version of the running build, shown in the page footer. CI sets this from
# `git describe --tags --always` at deploy time; "dev" is the local fallback.
APP_VERSION = os.getenv("APP_VERSION", "dev")

_REPO_URL = "https://github.com/michaelgreen-0/vapour"


def _release_url(version: str) -> str | None:
    """Map a version string to the GitHub page that best explains it."""
    if version == "dev":
        return None
    # A `git describe` build past a tag ("v0.1.0-3-gab12cd") points at its commit;
    # the sha follows the final "-g". An exact tag points at its release page.
    if "-g" in version:
        sha = version.rsplit("-g", 1)[1]
        return f"{_REPO_URL}/commit/{sha}"
    if version.startswith("v"):
        return f"{_REPO_URL}/releases/tag/{version}"
    return f"{_REPO_URL}/commit/{version}"


RELEASE_URL = _release_url(APP_VERSION)
