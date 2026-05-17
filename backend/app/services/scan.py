"""
ScanService — orchestrates scan creation and retrieval.

Étape 4: POST creates a pending scan and dispatches a Celery task.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.scan import Scan
from app.repositories import scan as scan_repo


class ScanService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create_scan(self, user_id: int, url: str) -> Scan:
        """Create a pending scan. Task dispatch is handled by the route."""
        return await scan_repo.create_pending_scan(self._db, user_id, url)

    async def get_scan(self, scan_id: int, user_id: int) -> Scan:
        scan = await scan_repo.get_scan_by_id(self._db, scan_id)
        if scan is None:
            raise ScanNotFoundError(scan_id)
        if scan.user_id != user_id:
            raise ScanForbiddenError(scan_id)
        return scan

    async def list_scans(self, user_id: int) -> list[Scan]:
        return await scan_repo.list_scans_for_user(self._db, user_id)


class ScanNotFoundError(Exception):
    def __init__(self, scan_id: int) -> None:
        super().__init__(f"Scan {scan_id} not found")
        self.scan_id = scan_id


class ScanForbiddenError(Exception):
    def __init__(self, scan_id: int) -> None:
        super().__init__(f"Scan {scan_id} belongs to another user")
        self.scan_id = scan_id
