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
