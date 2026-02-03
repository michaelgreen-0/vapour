import sys
import os
from unittest.mock import patch
import unittest
import pgpy

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.services.pgp_verifier import verify_login


class TestPgpVerifier(unittest.TestCase):
    def setUp(self):
        # Generate a new public/private keypair for each test
        self.key = pgpy.PGPKey.new(pgpy.constants.PubKeyAlgorithm.RSAEncryptOrSign, 4096)
        uid = pgpy.PGPUID.new('Test User', email='test@user.com')
        self.key.add_uid(uid, usage={pgpy.constants.KeyFlags.Sign},
                         hashes=[pgpy.constants.HashAlgorithm.SHA256])
        
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

    @patch('src.services.pgp_verifier.Logger')
    def test_verify_login_success(self, mock_logger):
        public_key_str = str(self.key.pubkey)
        clearsigned_str = str(self.clearsigned_message)

        is_valid, user_id = verify_login(public_key_str, clearsigned_str, self.challenge)

        self.assertEqual(user_id, str(self.key.fingerprint))
        self.assertTrue(is_valid)

    @patch('src.services.pgp_verifier.Logger')
    def test_verify_login_challenge_mismatch(self, mock_logger):
        public_key_str = str(self.key.pubkey)
        clearsigned_str = str(self.clearsigned_message)

        is_valid, user_id = verify_login(public_key_str, clearsigned_str, "wrong-challenge")

        self.assertFalse(is_valid)
        self.assertIsNone(user_id)

    @patch('src.services.pgp_verifier.Logger')
    def test_verify_login_no_signature(self, mock_logger):
        public_key_str = str(self.key.pubkey)
        clearsigned_str = self.challenge
        
        is_valid, user_id = verify_login(public_key_str, clearsigned_str, self.challenge)

        self.assertFalse(is_valid)
        self.assertIsNone(user_id)
    
    @patch('src.services.pgp_verifier.Logger')
    def test_verify_login_signer_id_not_found(self, mock_logger):
        wrong_key = pgpy.PGPKey.new(pgpy.constants.PubKeyAlgorithm.RSAEncryptOrSign, 2048)
        public_key_str = str(wrong_key.pubkey)
        clearsigned_str = str(self.clearsigned_message)

        is_valid, user_id = verify_login(public_key_str, clearsigned_str, self.challenge)

        self.assertFalse(is_valid)
        self.assertIsNone(user_id)

    @patch('src.services.pgp_verifier.Logger')
    def test_verify_login_invalid_signature(self, mock_logger):
        public_key_str = str(self.key.pubkey)
        clearsigned_str = str(self.clearsigned_message)
        # Tamper with the message
        clearsigned_str = clearsigned_str.replace(self.challenge, "tampered-challenge")

        is_valid, user_id = verify_login(public_key_str, clearsigned_str, self.challenge)

        self.assertFalse(is_valid)
        self.assertIsNone(user_id)

    @patch('src.services.pgp_verifier.Logger')
    def test_verify_login_exception(self, mock_logger):
        is_valid, user_id = verify_login("invalid-key", "invalid-message", "challenge")

        self.assertFalse(is_valid)
        self.assertIsNone(user_id)


if __name__ == '__main__':
    unittest.main()
