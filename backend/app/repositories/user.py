from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import User


class UserRepository:
    """Data-access layer for the User model."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_by_id(self, user_id: int) -> User | None:
        result = await self._db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        result = await self._db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def create(
        self,
        email: str,
        password_hash: str,
        full_name: str | None = None,
    ) -> User:
        user = User(email=email, password_hash=password_hash, full_name=full_name)
        self._db.add(user)
        await self._db.flush()  # assign PK without committing the transaction
        await self._db.refresh(user)
        return user
