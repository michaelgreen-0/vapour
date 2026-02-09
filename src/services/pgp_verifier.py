import pgpy
from ..logger import Logger


def verify_login(public_key_str, clearsigned_str, expected_challenge):
    logger = Logger()
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
