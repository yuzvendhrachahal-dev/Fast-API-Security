import hashlib
import secrets


def generate_otp() -> str:
    return str(secrets.randbelow(900000) + 100000)


def hash_otp(otp: str) -> str:
    return hashlib.sha256(
        otp.encode()
    ).hexdigest()