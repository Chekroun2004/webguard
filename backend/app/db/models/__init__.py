# Import all models here so Alembic's env.py can discover them via Base.metadata.
from app.db.models.api_key import ApiKey
from app.db.models.domain import DomainOwnership
from app.db.models.scan import Scan, Vulnerability
from app.db.models.scheduled_scan import ScheduledScan
from app.db.models.user import User
from app.db.models.webhook import Webhook

__all__ = [
    "ApiKey",
    "DomainOwnership",
    "Scan",
    "ScheduledScan",
    "User",
    "Vulnerability",
    "Webhook",
]
