# Import all models here so Alembic's env.py can discover them via Base.metadata.
from app.db.models.user import User  # noqa: F401

__all__ = ["User"]
