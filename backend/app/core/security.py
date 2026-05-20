from __future__ import annotations

import hashlib
import hmac
import secrets


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    raw_salt = bytes.fromhex(salt) if salt else secrets.token_bytes(16)
    password_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), raw_salt, 120_000).hex()
    return password_hash, raw_salt.hex()


def verify_password(password: str, password_hash: str, salt: str) -> bool:
    candidate_hash, _ = hash_password(password, salt)
    return hmac.compare_digest(candidate_hash, password_hash)


def generate_token() -> str:
    return secrets.token_urlsafe(32)
