import hashlib
import hmac
import secrets

from .config import settings

ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def generate_code() -> str:
    raw = "".join(secrets.choice(ALPHABET) for _ in range(16))
    parts = [raw[i:i + 4] for i in range(0, 16, 4)]
    return "MFTH-" + "-".join(parts)


def normalize_code(code: str) -> str:
    return code.strip().upper().replace("-", "").replace(" ", "")


def hash_code(code: str) -> str:
    key = settings.license_hmac_key.encode()
    msg = normalize_code(code).encode()
    return hmac.new(key, msg, hashlib.sha256).hexdigest()


def verify_code(code: str, stored_hash: str) -> bool:
    return hmac.compare_digest(hash_code(code), stored_hash)
