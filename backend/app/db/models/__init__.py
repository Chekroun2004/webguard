# Import all models here so Alembic's env.py can discover them via Base.metadata.
from app.db.models.user import User  # noqa: F401
from app.db.models.scan import Scan, Vulnerability  # noqa: F401
from app.db.models.domain import DomainOwnership  # noqa: F401

__all__ = ["User", "Scan", "Vulnerability", "DomainOwnership"]
