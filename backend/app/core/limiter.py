from fastapi import Request
from jose import JWTError, jwt
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100/minute"],
)


def get_user_id_key(request: Request) -> str:
    """Rate limit key based on authenticated user ID, fallback to IP."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:]
        try:
            payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
            return f"user:{payload.get('sub', 'anonymous')}"
        except JWTError:
            pass
    return get_remote_address(request)
