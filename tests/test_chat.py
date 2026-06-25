import sys
import os
import unittest
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.routes.chat import _origin_allowed, _valid_message


def fake_ws(headers):
    return SimpleNamespace(headers=headers)


FP = "497472E4EADD6B41F735D437F8FC9A8BDC9CF796"
OTHER_FP = "DEADBEEFDEADBEEFDEADBEEFDEADBEEFDEADBEEF"


class TestOriginAllowed(unittest.TestCase):
    def test_same_origin_allowed(self):
        ws = fake_ws({"origin": "https://vapour.chat", "host": "vapour.chat"})
        self.assertTrue(_origin_allowed(ws))

    def test_onion_same_origin_allowed(self):
        ws = fake_ws({"origin": "http://abc.onion", "host": "abc.onion"})
        self.assertTrue(_origin_allowed(ws))

    def test_cross_origin_rejected(self):
        ws = fake_ws({"origin": "https://evil.example", "host": "vapour.chat"})
        self.assertFalse(_origin_allowed(ws))

    def test_missing_origin_allowed_non_browser(self):
        self.assertTrue(_origin_allowed(fake_ws({"host": "vapour.chat"})))

    def test_origin_present_but_no_host_rejected(self):
        self.assertFalse(_origin_allowed(fake_ws({"origin": "https://vapour.chat"})))


class TestValidMessage(unittest.TestCase):
    def test_valid_key_exchange(self):
        self.assertTrue(
            _valid_message(
                {"type": "key_exchange", "target_user": FP, "publicKey": {"kty": "EC"}}
            )
        )

    def test_valid_encrypted_text(self):
        self.assertTrue(
            _valid_message(
                {
                    "type": "encrypted_text",
                    "target_user": OTHER_FP,
                    "content": {"iv": [1], "ciphertext": [2]},
                }
            )
        )

    def test_rejects_unknown_type(self):
        self.assertFalse(
            _valid_message({"type": "evil", "target_user": FP, "publicKey": {}})
        )

    def test_rejects_bad_target(self):
        self.assertFalse(
            _valid_message(
                {"type": "key_exchange", "target_user": "not-a-fp", "publicKey": {}}
            )
        )

    def test_rejects_key_exchange_without_public_key(self):
        self.assertFalse(_valid_message({"type": "key_exchange", "target_user": FP}))

    def test_rejects_encrypted_text_without_content_fields(self):
        self.assertFalse(
            _valid_message(
                {"type": "encrypted_text", "target_user": FP, "content": {"iv": [1]}}
            )
        )

    def test_rejects_non_dict(self):
        for value in (None, "x", 5, ["a"]):
            self.assertFalse(_valid_message(value), value)


if __name__ == "__main__":
    unittest.main()
