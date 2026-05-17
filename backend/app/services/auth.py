from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.db.models.user import User
from app.repositories.user import UserRepository
from app.schemas.auth import TokenPair
from app.schemas.user import UserCreate


class AuthService:
    """Business logic for authentication."""

    def __init__(self, db: AsyncSession) -> None:
        self._repo = UserRepository(db)

    async def register(self, data: UserCreate) -> User:
        """Create a new user. Raises ValueError if the email is already taken."""
        if await self._repo.get_by_email(data.email):
            raise ValueError("Un compte existe déjà avec cet email.")
        return await self._repo.create(
            email=data.email,
            password_hash=hash_password(data.password),
            full_name=data.full_name,
        )

    async def login(self, email: str, password: str) -> TokenPair:
        """Validate credentials and return a token pair."""
        user = await self._repo.get_by_email(email)
        if not user or not verify_password(password, user.password_hash):
            raise ValueError("Email ou mot de passe incorrect.")
        if not user.is_active:
            raise ValueError("Compte désactivé.")
        return TokenPair(
            access_token=create_access_token(user.id),
            refresh_token=create_refresh_token(user.id),
        )

    async def refresh(self, refresh_token: str) -> TokenPair:
        """Issue a new token pair from a valid refresh token."""
        try:
            user_id = decode_token(refresh_token, expected_type="refresh")
        except ValueError as exc:
            raise ValueError("Refresh token invalide ou expiré.") from exc

        user = await self._repo.get_by_id(user_id)
        if not user or not user.is_active:
            raise ValueError("Utilisateur introuvable ou désactivé.")
        return TokenPair(
            access_token=create_access_token(user.id),
            refresh_token=create_refresh_token(user.id),
        )

    async def get_current_user(self, access_token: str) -> User:
        """Return the user identified by an access token."""
        try:
            user_id = decode_token(access_token, expected_type="access")
        except ValueError as exc:
            raise ValueError("Access token invalide ou expiré.") from exc

        user = await self._repo.get_by_id(user_id)
        if not user or not user.is_active:
            raise ValueError("Utilisateur introuvable ou désactivé.")
        return user
