import sys
import os
import unittest
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.services.rate_limit import is_rate_limited, client_ip


class FakeRedis:
    def __init__(self):
        self.counts = {}
        self.expires = {}

    def incr(self, key):
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key]

    def expire(self, key, seconds):
        self.expires[key] = seconds


class TestRateLimit(unittest.TestCase):
    def test_public_ip_blocked_past_limit(self):
        r = FakeRedis()
        allowed = [
            is_rate_limited(r, "8.8.8.8", "login", limit=3, window=60)
            for _ in range(3)
        ]
        self.assertEqual(allowed, [False, False, False])
        self.assertTrue(is_rate_limited(r, "8.8.8.8", "login", limit=3, window=60))

    def test_expire_set_once_on_first_hit(self):
        r = FakeRedis()
        for _ in range(5):
            is_rate_limited(r, "8.8.8.8", "login", limit=10, window=60)
        # exactly one key, expiry set near the window
        self.assertEqual(len(r.expires), 1)
        self.assertEqual(next(iter(r.expires.values())), 61)

    def test_private_ip_never_limited(self):
        r = FakeRedis()
        for ip in ("10.0.0.5", "192.168.1.9", "127.0.0.1", "172.16.0.1"):
            results = [
                is_rate_limited(r, ip, "login", limit=1, window=60) for _ in range(5)
            ]
            self.assertTrue(all(x is False for x in results), ip)
        # private traffic must not even touch Redis
        self.assertEqual(r.counts, {})

    def test_unparseable_ip_not_limited(self):
        r = FakeRedis()
        self.assertFalse(is_rate_limited(r, "unknown", "login", limit=1, window=60))

    def test_scopes_are_independent(self):
        r = FakeRedis()
        self.assertFalse(is_rate_limited(r, "8.8.8.8", "index", limit=1, window=60))
        # different scope, fresh budget
        self.assertFalse(is_rate_limited(r, "8.8.8.8", "login", limit=1, window=60))

    def test_client_ip_reads_request(self):
        req = SimpleNamespace(client=SimpleNamespace(host="1.2.3.4"))
        self.assertEqual(client_ip(req), "1.2.3.4")

    def test_client_ip_missing_client(self):
        self.assertEqual(client_ip(SimpleNamespace(client=None)), "unknown")


if __name__ == "__main__":
    unittest.main()
