from fastapi import Depends, Header, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import User
from app.db.session import get_db
from app.repositories.user import UserRepository
from app.services.api_key import ApiKeyService
from app.services.auth import AuthService

_bearer = HTTPBearer(auto_error=False)


async def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    """FastAPI dependency that provides an AuthService bound to the current DB session."""
    return AuthService(db)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    token: str | None = Query(default=None),  # fallback for EventSource (no custom headers)
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    db: AsyncSession = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
) -> User:
    """Resolve auth credentials to a User, or raise 401.

    Accepted credential sources, in order:
    1. ``X-API-Key`` header — programmatic access via long-lived API key.
    2. ``Authorization: Bearer <jwt>`` header — interactive user JWT.
    3. ``?token=<jwt>`` query param — fallback for SSE / EventSource.
    """
    if x_api_key:
        api_key = await ApiKeyService(db).resolve(x_api_key)
        if api_key is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Clé API invalide ou révoquée."
            )
        user = await UserRepository(db).get_by_id(api_key.user_id)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Utilisateur introuvable ou désactivé.",
            )
        return user

    raw_token = (credentials.credentials if credentials else None) or token
    if not raw_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Non authentifié.")
    try:
        return await auth_service.get_current_user(raw_token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
