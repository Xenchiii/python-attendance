import hashlib
import hmac
import re
import secrets


def derive(password, salt):
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000, 32)


def hash_password(password):
    salt = secrets.token_bytes(16)
    return salt.hex() + ":" + derive(password, salt).hex()


def verify_password(password, stored):
    parts = (stored or "").split(":")
    if len(parts) != 2:
        return False
    try:
        salt = bytes.fromhex(parts[0])
        expected = bytes.fromhex(parts[1])
    except ValueError:
        return False
    return hmac.compare_digest(derive(password, salt), expected)


def new_token():
    return secrets.token_hex(24)


def sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def valid_sid(value):
    return bool(value) and re.fullmatch(r"[a-f0-9]+", value) is not None
