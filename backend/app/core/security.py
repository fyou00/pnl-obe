from datetime import UTC, datetime, timedelta
from uuid import uuid4

import bcrypt
import jwt

from app.core.config import Settings
from app.models.identity import User


def hash_password(password: str) -> str:
    raw = password.encode("utf-8")
    if not 12 <= len(raw) <= 72:
        raise ValueError("Password harus 12–72 byte UTF-8")
    return bcrypt.hashpw(raw, bcrypt.gensalt(rounds=12)).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    raw = password.encode("utf-8")
    if len(raw) > 72:
        return False
    try:
        return bcrypt.checkpw(raw, password_hash.encode("ascii"))
    except (ValueError, TypeError, UnicodeError):
        return False


def create_access_token(user: User, settings: Settings) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "sub": str(user.id),
            "iat": now,
            "exp": now + timedelta(minutes=settings.access_token_minutes),
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
            "jti": str(uuid4()),
            "ver": user.token_version,
            "type": "access",
        },
        settings.jwt_secret_key.get_secret_value(),
        algorithm="HS256",
    )


def decode_access_token(token: str, settings: Settings) -> dict:
    claims = jwt.decode(
        token,
        settings.jwt_secret_key.get_secret_value(),
        algorithms=["HS256"],
        audience=settings.jwt_audience,
        issuer=settings.jwt_issuer,
        options={"require": ["sub", "exp", "iat", "iss", "aud", "jti", "ver", "type"]},
    )
    if claims["type"] != "access" or type(claims["ver"]) is not int:
        raise jwt.InvalidTokenError("Invalid access token")
    return claims
