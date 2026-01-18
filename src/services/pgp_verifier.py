import pgpy
import traceback

def verify_login(public_key_str, clearsigned_str, expected_challenge):
    try:
        clearsigned_str = clearsigned_str.replace('\u202f', ' ').replace('\r\n', '\n').strip()
        public_key_str = public_key_str.replace('\u202f', ' ').strip()

        key, _ = pgpy.PGPKey.from_blob(public_key_str)
        msg = pgpy.PGPMessage.from_blob(clearsigned_str)
        
        if str(msg.message).strip() != expected_challenge.strip():
            print("Challenge mismatch")
            return False, None

        if not msg.signatures:
            print("No signatures")
            return False, None

        signer_id = msg.signatures[0].signer
        known_ids = {key.fingerprint.keyid} | set(key.subkeys)
        
        if signer_id not in known_ids:
            print(f"Signing ID {signer_id} not in known IDs {known_ids}")
            return False, None

        verification = key.verify(msg)
        
        print(f"Verification result: {verification}")
        
        if verification:
            return True, str(key.fingerprint.keyid)
        return False, None

    except Exception as e:
        print(f"Exception: {e}")
        
        traceback.print_exc()
        return False, None