import os
from dotenv import load_dotenv

load_dotenv()

CHALLENGE_LIFETIME = os.getenv("CHALLENGE_LIFETIME")
REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = os.getenv("REDIS_PORT")
