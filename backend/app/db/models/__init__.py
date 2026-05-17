# Import all models here so Alembic's env.py can discover them via Base.metadata.
from app.db.models.domain import DomainOwnership
from app.db.models.scan import Scan, Vulnerability
from app.db.models.user import User

__all__ = ["DomainOwnership", "Scan", "User", "Vulnerability"]
