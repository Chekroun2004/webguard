from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

_pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(password: str) -> str:
    """Return an argon2 hash of the given plain-text password."""
    return _pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if *plain* matches *hashed*."""
    return _pwd_context.verify(plain, hashed)


def _create_token(payload: dict[str, Any], expires_delta: timedelta) -> str:
    data = payload.copy()
    data["exp"] = datetime.now(timezone.utc) + expires_delta
    return jwt.encode(data, settings.secret_key, algorithm="HS256")


def create_access_token(user_id: int) -> str:
    return _create_token(
        {"sub": str(user_id), "type": "access"},
        timedelta(minutes=settings.access_token_expire_minutes),
    )


def create_refresh_token(user_id: int) -> str:
    return _create_token(
        {"sub": str(user_id), "type": "refresh"},
        timedelta(days=settings.refresh_token_expire_days),
    )


def decode_token(token: str, expected_type: str) -> int:
    """Decode a JWT and return the user_id.

    Raises:
        ValueError: if the token is invalid, expired, or of the wrong type.
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    except JWTError as exc:
        raise ValueError("Token invalide ou expiré.") from exc

    if payload.get("type") != expected_type:
        raise ValueError(f"Type de token attendu : '{expected_type}'.")

    sub = payload.get("sub")
    if sub is None:
        raise ValueError("Token sans 'sub'.")

    return int(sub)
