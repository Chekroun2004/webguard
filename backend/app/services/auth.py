from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_refresh_token,
    create_totp_pending_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.db.models.user import User
from app.repositories.user import UserRepository
from app.schemas.auth import LoginResponse, TokenPair
from app.schemas.user import UserCreate
from app.services.totp_service import TotpService


class AuthService:
    """Business logic for authentication."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db
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

    async def login(self, email: str, password: str) -> LoginResponse:
        """Validate credentials. If 2FA is enabled, return a pending token instead."""
        user = await self._repo.get_by_email(email)
        if not user or not verify_password(password, user.password_hash):
            raise ValueError("Email ou mot de passe incorrect.")
        if not user.is_active:
            raise ValueError("Compte désactivé.")
        if user.totp_enabled:
            return LoginResponse(
                totp_required=True,
                pending_token=create_totp_pending_token(user.id),
            )
        return LoginResponse(
            access_token=create_access_token(user.id),
            refresh_token=create_refresh_token(user.id),
        )

    async def login_totp(self, pending_token: str, code: str) -> TokenPair:
        """Second login step — verify the TOTP code, return full token pair."""
        try:
            user_id = decode_token(pending_token, expected_type="totp_pending")
        except ValueError as exc:
            raise ValueError("Session 2FA invalide ou expirée.") from exc

        user = await self._repo.get_by_id(user_id)
        if not user or not user.is_active:
            raise ValueError("Utilisateur introuvable ou désactivé.")
        if not user.totp_enabled:
            raise ValueError("2FA non activée sur ce compte.")

        if not TotpService(self._db).verify(user, code):
            raise ValueError("Code 2FA invalide.")

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
