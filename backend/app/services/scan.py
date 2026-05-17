"""
ScanService — orchestrates scanner execution and persistence.

Étape 3: synchronous (inline) execution.
Étape 4: replaced by Celery task dispatch.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.scan import Scan
from app.repositories import scan as scan_repo
from app.scanners.headers import HeadersScanner


class ScanService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def run_scan(self, user_id: int, url: str) -> Scan:
        """Run all enabled scanners and persist results."""
        scanners = [HeadersScanner()]
        all_findings = []
        for scanner in scanners:
            findings = await scanner.scan(url, config={})
            all_findings.extend(findings)

        scan = await scan_repo.create_scan(
            db=self._db,
            user_id=user_id,
            url=url,
            findings=all_findings,
            status="completed",
        )
        return scan

    async def get_scan(self, scan_id: int, user_id: int) -> Scan:
        """Return scan if it belongs to user_id, else raise."""
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
