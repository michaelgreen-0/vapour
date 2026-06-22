import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
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


if __name__ == "__main__":
    unittest.main()
