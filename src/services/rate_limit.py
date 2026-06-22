import ipaddress
import time

from fastapi import Request


def client_ip(request: Request) -> str:
    """Best-effort client IP.

    Behind Caddy, uvicorn's --proxy-headers rewrites request.client to the
    real client taken from X-Forwarded-For, so this returns the end user's
    address rather than the proxy's.
    """
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _is_public(ip: str) -> bool:
    try:
        return ipaddress.ip_address(ip).is_global
    except ValueError:
        return False


def is_rate_limited(
    redis_client, ip: str, scope: str, limit: int, window: int
) -> bool:
    """Fixed-window per-IP rate limit backed by Redis.

    Returns True when the caller has exceeded ``limit`` requests within the
    current ``window`` (seconds) for the given ``scope``.

    Only public (globally routable) IPs are limited. Onion traffic arrives via
    the local Tor daemon and internal calls come from private ranges, so they
    all share a single address -- limiting per-IP there would lock every onion
    user out at once. Those paths are defended by Tor's onion-service PoW and
    the server-wide --limit-concurrency cap instead.
    """
    if not _is_public(ip):
        return False

    key = f"rl:{scope}:{ip}:{int(time.time()) // window}"
    count = redis_client.incr(key)
    if count == 1:
        # First hit in this window: set the key to expire so buckets don't
        # accumulate. Slightly over the window to tolerate clock skew.
        redis_client.expire(key, window + 1)
    return count > limit
