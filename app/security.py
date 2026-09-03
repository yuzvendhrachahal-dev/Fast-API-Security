import os
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from dotenv import load_dotenv

load_dotenv()

from argon2 import PasswordHasher

password_hasher = PasswordHasher()

def hash_password(password: str) -> str:
    return password_hasher.hash(password)

def verify_password(
    password: str,
    password_hash: str
) -> bool:

    try:
        password_hasher.verify(
            password_hash,
            password
        )
        return True

    except Exception:
        return False



JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = os.getenv(
    "JWT_ALGORITHM",
    "HS256"
)
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30")
)


def create_access_token(user_id: str, role: str) -> str:

    now = datetime.now(timezone.utc)

    expire = now + timedelta(
        minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": user_id,
        "role": role,
        "token_type": "access",
        "iat": now,
        "exp": expire,
        "jti": str(uuid.uuid4())
    }

    return jwt.encode(
        payload,
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM
    )

def decode_access_token(token: str):

    try:
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM]
        )

        if payload.get("token_type") != "access":
            return None

        if not payload.get("sub"):
            return None

        return payload

    except jwt.InvalidTokenError:
        return None
