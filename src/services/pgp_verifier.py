import pgpy
import logging
from pgpy.constants import HashAlgorithm, PubKeyAlgorithm

# --- Acceptance policy -------------------------------------------------------
#
# Identity here IS the key fingerprint, so a valid signature already proves the
# user controls that key. These checks layer an explicit *strength* policy on
# top so we don't accept signatures made with broken primitives.
#
# Known limitation: pgpy does not implement OpenPGP revocation or key-flag
# checks (it emits a warning saying so), so we cannot reject a key the owner has
# revoked. We DO reject expired keys. If revocation enforcement becomes
# required, it needs a different OpenPGP library or an external keyserver check.

# Signature digest algorithms we refuse (collision-broken or weak).
_WEAK_HASHES = {HashAlgorithm.MD5, HashAlgorithm.SHA1, HashAlgorithm.RIPEMD160}

# Public-key algorithms we accept, with a minimum size for the RSA family.
_RSA_ALGOS = {
    PubKeyAlgorithm.RSAEncryptOrSign,
    PubKeyAlgorithm.RSAEncrypt,
    PubKeyAlgorithm.RSASign,
}
_MIN_RSA_BITS = 2048
_ALLOWED_ECC_ALGOS = {PubKeyAlgorithm.ECDSA, PubKeyAlgorithm.EdDSA}


def _signature_policy_ok(signature, logger) -> bool:
    if signature.hash_algorithm in _WEAK_HASHES:
        logger.error(f"Rejected weak signature hash: {signature.hash_algorithm}")
        return False
    return True


def _key_policy_ok(key, logger) -> bool:
    if key.is_expired:
        logger.error("Rejected expired key")
        return False

    algo = key.key_algorithm
    if algo in _RSA_ALGOS:
        if (key.key_size or 0) < _MIN_RSA_BITS:
            logger.error(f"Rejected RSA key smaller than {_MIN_RSA_BITS} bits")
            return False
        return True
    if algo in _ALLOWED_ECC_ALGOS:
        return True

    logger.error(f"Rejected unsupported key algorithm: {algo}")
    return False


def verify_login(public_key_str, clearsigned_str, expected_challenge):
    logger = logging.getLogger(__name__)
    try:
        clearsigned_str = (
            clearsigned_str.replace("\u202f", " ").replace("\r\n", "\n").strip()
        )
        public_key_str = public_key_str.replace("\u202f", " ").strip()

        key, _ = pgpy.PGPKey.from_blob(public_key_str)
        msg = pgpy.PGPMessage.from_blob(clearsigned_str)

        if str(msg.message).strip() != expected_challenge.strip():
            logger.error("Challenge mismatch")
            return False, None

        if not msg.signatures:
            logger.error("No signatures")
            return False, None

        signer_id = msg.signatures[0].signer
        known_ids = {key.fingerprint.keyid} | set(key.subkeys)

        if signer_id not in known_ids:
            logger.error(f"Key id in signature not found in public key")
            return False, None

        # Enforce the strength policy before trusting the signature.
        if not _key_policy_ok(key, logger) or not _signature_policy_ok(
            msg.signatures[0], logger
        ):
            return False, None

        verification = key.verify(msg)

        logger.info(f"Verification result: {verification}")

        if verification:
            return True, str(
                key.fingerprint
            )  # Return the full fingerprint instead of the keyid
        return False, None

    except Exception as e:
        logger.error(f"Exception: {e}", exc_info=True)
        return False, None
