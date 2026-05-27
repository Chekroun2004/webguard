"""
API key service — generate, hash, look up, revoke.

Keys are 32 random bytes (URL-safe base64) prefixed with ``wgk_`` and shown to
the user EXACTLY ONCE on creation. We store only the SHA-256 of the full key
(plus the public prefix for display). Random 256-bit secrets do not need a
slow KDF — sha256 is sufficient and lets the API auth path stay synchronous.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.api_key import ApiKey
from app.repositories.api_key import (
    create_api_key,
    get_api_key_by_hash,
    get_api_key_by_id,
    list_api_keys_for_user,
)

KEY_PREFIX = "wgk_"
KEY_BODY_BYTES = 32  # → ~43 chars of url-safe base64


class ApiKeyNotFoundError(Exception):
    pass


class ApiKeyForbiddenError(Exception):
    pass


def hash_key(plaintext: str) -> str:
    return hashlib.sha256(plaintext.encode("utf-8")).hexdigest()


def _generate_plaintext() -> tuple[str, str]:
    body = secrets.token_urlsafe(KEY_BODY_BYTES)
    full = f"{KEY_PREFIX}{body}"
    # Public prefix shown in listings: wgk_ + first 4 chars of the random body.
    public_prefix = f"{KEY_PREFIX}{body[:4]}"
    return full, public_prefix


class ApiKeyService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, user_id: int, name: str) -> tuple[ApiKey, str]:
        """Generate a new key. Returns (record, plaintext) — caller MUST surface
        the plaintext to the user exactly once.
        """
        plaintext, public_prefix = _generate_plaintext()
        record = await create_api_key(
            self._db,
            user_id=user_id,
            name=name,
            prefix=public_prefix,
            hashed_key=hash_key(plaintext),
        )
        return record, plaintext

    async def list_for_user(self, user_id: int) -> list[ApiKey]:
        return await list_api_keys_for_user(self._db, user_id)

    async def revoke(self, key_id: int, user_id: int) -> None:
        record = await get_api_key_by_id(self._db, key_id)
        if record is None:
            raise ApiKeyNotFoundError
        if record.user_id != user_id:
            raise ApiKeyForbiddenError
        if record.revoked_at is None:
            record.revoked_at = datetime.now(UTC)
            await self._db.flush()

    async def resolve(self, plaintext: str) -> ApiKey | None:
        """Return the active ApiKey for a plaintext token, or None.

        Bumps ``last_used_at`` as a side effect when the key is active.
        """
        if not plaintext.startswith(KEY_PREFIX):
            return None
        record = await get_api_key_by_hash(self._db, hash_key(plaintext))
        if record is None or record.revoked_at is not None:
            return None
        record.last_used_at = datetime.now(UTC)
        await self._db.flush()
        return record
