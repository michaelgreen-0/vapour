import sys
import os
import time
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.services import session
from src.services.session import sign_user_id, unsign_user_id


class TestSession(unittest.TestCase):
    fingerprint = "ABCD1234ABCD1234ABCD1234ABCD1234ABCD1234"

    def test_round_trip(self):
        token = sign_user_id(self.fingerprint)
        self.assertNotEqual(token, self.fingerprint)
        self.assertEqual(unsign_user_id(token), self.fingerprint)

    def test_tampered_value_rejected(self):
        token = sign_user_id(self.fingerprint)
        _, _, signature = token.rpartition(".")
        forged = f"DEADBEEFDEADBEEFDEADBEEFDEADBEEFDEADBEEF.{signature}"
        self.assertIsNone(unsign_user_id(forged))

    def test_bad_signature_rejected(self):
        self.assertIsNone(unsign_user_id(f"{self.fingerprint}.deadbeef"))

    def test_unsigned_value_rejected(self):
        # The old behaviour: a bare fingerprint with no signature must fail.
        self.assertIsNone(unsign_user_id(self.fingerprint))

    def test_empty_and_malformed(self):
        for token in (None, "", "no-dot", ".", f"{self.fingerprint}.", "."):
            self.assertIsNone(unsign_user_id(token), token)

    def _signed_at(self, issued_at: int) -> str:
        # Build a validly-signed token with an arbitrary issue time.
        payload = f"{self.fingerprint}.{issued_at}"
        return f"{payload}.{session._signature(payload)}"

    def test_expired_token_rejected(self):
        old = int(time.time()) - session.SESSION_LIFETIME - 10
        self.assertIsNone(unsign_user_id(self._signed_at(old)))

    def test_future_dated_token_rejected(self):
        future = int(time.time()) + 600
        self.assertIsNone(unsign_user_id(self._signed_at(future)))

    def test_within_lifetime_accepted(self):
        recent = int(time.time()) - 5
        self.assertEqual(unsign_user_id(self._signed_at(recent)), self.fingerprint)

    def test_non_numeric_issue_time_rejected(self):
        payload = f"{self.fingerprint}.notanumber"
        token = f"{payload}.{session._signature(payload)}"
        self.assertIsNone(unsign_user_id(token))


if __name__ == "__main__":
    unittest.main()
