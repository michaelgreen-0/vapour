import sys
import os
from unittest.mock import patch, MagicMock
from types import SimpleNamespace
import unittest
import pgpy

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.services.pgp_verifier import verify_login


class TestPgpVerifier(unittest.TestCase):
    def setUp(self):
        # Generate a new public/private keypair for each test
        self.key = pgpy.PGPKey.new(
            pgpy.constants.PubKeyAlgorithm.RSAEncryptOrSign, 4096
        )
        uid = pgpy.PGPUID.new("Test User", email="test@user.com")
        self.key.add_uid(
            uid,
            usage={pgpy.constants.KeyFlags.Sign},
            hashes=[pgpy.constants.HashAlgorithm.SHA256],
        )

        self.challenge = "test-challenge"
        message = pgpy.PGPMessage.new(self.challenge)
        signature = self.key.sign(message)

        # Had troubles with getting a truly clearsigned signature. Manually construct it instead.
        self.clearsigned_message = (
            "-----BEGIN PGP SIGNED MESSAGE-----\n"
            "Hash: SHA256\n"
            "\n"
            f"{self.challenge}\n"
            f"{str(signature)}"
        )

    @patch("src.services.pgp_verifier.logging")
    def test_verify_login_success(self, mock_logger):
        public_key_str = str(self.key.pubkey)
        clearsigned_str = str(self.clearsigned_message)

        is_valid, user_id = verify_login(
            public_key_str, clearsigned_str, self.challenge
        )

        self.assertEqual(user_id, str(self.key.fingerprint))
        self.assertTrue(is_valid)

    @patch("src.services.pgp_verifier.logging")
    def test_verify_login_challenge_mismatch(self, mock_logger):
        public_key_str = str(self.key.pubkey)
        clearsigned_str = str(self.clearsigned_message)

        is_valid, user_id = verify_login(
            public_key_str, clearsigned_str, "wrong-challenge"
        )

        self.assertFalse(is_valid)
        self.assertIsNone(user_id)

    @patch("src.services.pgp_verifier.logging")
    def test_verify_login_no_signature(self, mock_logger):
        public_key_str = str(self.key.pubkey)
        clearsigned_str = self.challenge

        is_valid, user_id = verify_login(
            public_key_str, clearsigned_str, self.challenge
        )

        self.assertFalse(is_valid)
        self.assertIsNone(user_id)

    @patch("src.services.pgp_verifier.logging")
    def test_verify_login_signer_id_not_found(self, mock_logger):
        wrong_key = pgpy.PGPKey.new(
            pgpy.constants.PubKeyAlgorithm.RSAEncryptOrSign, 2048
        )
        public_key_str = str(wrong_key.pubkey)
        clearsigned_str = str(self.clearsigned_message)

        is_valid, user_id = verify_login(
            public_key_str, clearsigned_str, self.challenge
        )

        self.assertFalse(is_valid)
        self.assertIsNone(user_id)

    @patch("src.services.pgp_verifier.logging")
    def test_verify_login_invalid_signature(self, mock_logger):
        public_key_str = str(self.key.pubkey)
        clearsigned_str = str(self.clearsigned_message)
        # Tamper with the message
        clearsigned_str = clearsigned_str.replace(self.challenge, "tampered-challenge")

        is_valid, user_id = verify_login(
            public_key_str, clearsigned_str, self.challenge
        )

        self.assertFalse(is_valid)
        self.assertIsNone(user_id)

    @patch("src.services.pgp_verifier.logging")
    def test_verify_login_exception(self, mock_logger):
        is_valid, user_id = verify_login("invalid-key", "invalid-message", "challenge")

        self.assertFalse(is_valid)
        self.assertIsNone(user_id)

    @patch("src.services.pgp_verifier.logging")
    def test_rejects_weak_rsa_key(self, mock_logger):
        # A correctly-signed challenge from an undersized (1024-bit) RSA key
        # must still be rejected by the strength policy.
        weak = pgpy.PGPKey.new(pgpy.constants.PubKeyAlgorithm.RSAEncryptOrSign, 1024)
        uid = pgpy.PGPUID.new("Weak", email="weak@user.com")
        weak.add_uid(
            uid,
            usage={pgpy.constants.KeyFlags.Sign},
            hashes=[pgpy.constants.HashAlgorithm.SHA256],
        )
        signature = weak.sign(pgpy.PGPMessage.new(self.challenge))
        clearsigned = (
            "-----BEGIN PGP SIGNED MESSAGE-----\n"
            "Hash: SHA256\n\n"
            f"{self.challenge}\n{str(signature)}"
        )

        is_valid, user_id = verify_login(
            str(weak.pubkey), clearsigned, self.challenge
        )

        self.assertFalse(is_valid)
        self.assertIsNone(user_id)

    @patch("src.services.pgp_verifier.logging")
    def test_rejects_weak_hash_algorithm(self, mock_logger):
        # Strong key, but the signature uses SHA-1.
        signature = self.key.sign(
            pgpy.PGPMessage.new(self.challenge),
            hash=pgpy.constants.HashAlgorithm.SHA1,
        )
        clearsigned = (
            "-----BEGIN PGP SIGNED MESSAGE-----\n"
            "Hash: SHA1\n\n"
            f"{self.challenge}\n{str(signature)}"
        )

        is_valid, user_id = verify_login(
            str(self.key.pubkey), clearsigned, self.challenge
        )

        self.assertFalse(is_valid)
        self.assertIsNone(user_id)


class TestPgpPolicyHelpers(unittest.TestCase):
    """Unit tests for the policy gates, independent of full PGP parsing."""

    def setUp(self):
        from src.services import pgp_verifier

        self.pv = pgp_verifier
        self.logger = MagicMock()

    def _key(self, **kw):
        defaults = dict(
            is_expired=False,
            key_algorithm=pgpy.constants.PubKeyAlgorithm.RSAEncryptOrSign,
            key_size=4096,
        )
        defaults.update(kw)
        return SimpleNamespace(**defaults)

    def test_strong_rsa_ok(self):
        self.assertTrue(self.pv._key_policy_ok(self._key(), self.logger))

    def test_expired_rejected(self):
        self.assertFalse(
            self.pv._key_policy_ok(self._key(is_expired=True), self.logger)
        )

    def test_small_rsa_rejected(self):
        self.assertFalse(
            self.pv._key_policy_ok(self._key(key_size=1024), self.logger)
        )

    def test_dsa_rejected(self):
        self.assertFalse(
            self.pv._key_policy_ok(
                self._key(key_algorithm=pgpy.constants.PubKeyAlgorithm.DSA),
                self.logger,
            )
        )

    def test_ecdsa_ok(self):
        self.assertTrue(
            self.pv._key_policy_ok(
                self._key(key_algorithm=pgpy.constants.PubKeyAlgorithm.ECDSA),
                self.logger,
            )
        )

    def test_signature_hash_policy(self):
        ok = SimpleNamespace(hash_algorithm=pgpy.constants.HashAlgorithm.SHA256)
        weak = SimpleNamespace(hash_algorithm=pgpy.constants.HashAlgorithm.SHA1)
        self.assertTrue(self.pv._signature_policy_ok(ok, self.logger))
        self.assertFalse(self.pv._signature_policy_ok(weak, self.logger))


if __name__ == "__main__":
    unittest.main()
