"""
ScanDiffService — compare two scans of the same URL and return added/removed/unchanged findings.
"""

from __future__ import annotations

from app.db.models.scan import Scan, Vulnerability
from app.services.scan import ScanForbiddenError, ScanNotFoundError, ScanService
from sqlalchemy.ext.asyncio import AsyncSession


def _key(v: Vulnerability) -> tuple[str, str, str]:
    return (v.name, v.severity, v.evidence or "")


class ScanUrlMismatchError(Exception):
    """Two scans being compared have different URLs."""


class ScanDiffService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._scan_service = ScanService(db)

    async def diff(self, old_id: int, new_id: int, user_id: int) -> dict:
        """Compare two scans (both must belong to user_id and have the same URL)."""
        old_scan = await self._scan_service.get_scan(old_id, user_id)
        new_scan = await self._scan_service.get_scan(new_id, user_id)

        if old_scan.url.rstrip("/") != new_scan.url.rstrip("/"):
            raise ScanUrlMismatchError(
                f"Cannot diff scans of different URLs: {old_scan.url} vs {new_scan.url}"
            )

        old_keys = {_key(v): v for v in old_scan.vulnerabilities}
        new_keys = {_key(v): v for v in new_scan.vulnerabilities}

        added = [v for k, v in new_keys.items() if k not in old_keys]
        removed = [v for k, v in old_keys.items() if k not in new_keys]
        unchanged = [v for k, v in new_keys.items() if k in old_keys]

        return {
            "old_scan": _scan_summary(old_scan),
            "new_scan": _scan_summary(new_scan),
            "added": added,
            "removed": removed,
            "unchanged": unchanged,
        }


def _scan_summary(scan: Scan) -> dict:
    return {
        "id": scan.id,
        "url": str(scan.url),
        "created_at": scan.created_at,
        "finished_at": scan.finished_at,
        "total": len(scan.vulnerabilities),
    }


__all__ = ["ScanDiffService", "ScanUrlMismatchError", "ScanNotFoundError", "ScanForbiddenError"]
