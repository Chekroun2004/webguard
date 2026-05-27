"""TOTP enrollment / confirm / disable business logic."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import DecryptionError, decrypt_json, encrypt_json
from app.db.models.user import User
from app.services import totp as totp_lib


class InvalidTotpCodeError(Exception):
    pass


class TotpNotEnrolledError(Exception):
    pass


class TotpService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def enroll(self, user: User) -> tuple[str, str]:
        """Generate (or replace) a secret. Returns (secret, otpauth_uri).

        The secret is plaintext here so the user can scan it; we persist it
        encrypted via app.core.crypto. ``totp_enabled`` is reset to False —
        the user must confirm with a fresh code before 2FA is active.
        """
        secret = totp_lib.generate_secret()
        user.totp_secret_encrypted = encrypt_json({"secret": secret})
        user.totp_enabled = False
        user.totp_confirmed_at = None
        await self._db.flush()
        return secret, totp_lib.build_otpauth_uri(secret, user.email)

    async def confirm(self, user: User, code: str) -> None:
        secret = self._read_secret(user)
        if not totp_lib.verify_code(secret, code):
            raise InvalidTotpCodeError
        user.totp_enabled = True
        user.totp_confirmed_at = datetime.now(UTC)
        await self._db.flush()

    async def disable(self, user: User, code: str) -> None:
        if not user.totp_enabled:
            raise TotpNotEnrolledError
        secret = self._read_secret(user)
        if not totp_lib.verify_code(secret, code):
            raise InvalidTotpCodeError
        user.totp_secret_encrypted = None
        user.totp_enabled = False
        user.totp_confirmed_at = None
        await self._db.flush()

    def verify(self, user: User, code: str) -> bool:
        """Stateless check used by the two-step login flow."""
        if not user.totp_enabled:
            return False
        try:
            secret = self._read_secret(user)
        except (TotpNotEnrolledError, DecryptionError):
            return False
        return totp_lib.verify_code(secret, code)

    def _read_secret(self, user: User) -> str:
        if not user.totp_secret_encrypted:
            raise TotpNotEnrolledError
        try:
            payload = decrypt_json(user.totp_secret_encrypted)
        except DecryptionError as exc:
            raise TotpNotEnrolledError from exc
        return payload["secret"]
