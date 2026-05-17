"""Domain ownership service — verification logic (file & DNS)."""
from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import urlparse

import dns.asyncresolver
import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.domain import DomainOwnership
from app.repositories.domain import (
    create_domain_record,
    get_domain_by_id,
    get_domain_by_user_and_name,
    list_domains_for_user,
)


class DomainAlreadyExistsError(Exception):
    pass


class DomainNotFoundError(Exception):
    pass


class DomainForbiddenError(Exception):
    pass


class DomainVerificationError(Exception):
    pass


def normalize_domain(raw: str) -> str:
    """Return bare hostname from any URL-like or plain string (lowercase)."""
    raw = raw.strip()
    if "://" not in raw:
        raw = "https://" + raw
    host = urlparse(raw).hostname or ""
    return host.lower()


class DomainService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def register(self, user_id: int, domain: str, method: str) -> DomainOwnership:
        domain = normalize_domain(domain)
        existing = await get_domain_by_user_and_name(self._db, user_id, domain)
        if existing is not None:
            raise DomainAlreadyExistsError(domain)
        return await create_domain_record(self._db, user_id, domain, method)

    async def list_domains(self, user_id: int) -> list[DomainOwnership]:
        return await list_domains_for_user(self._db, user_id)

    async def get_domain(self, domain_id: int, user_id: int) -> DomainOwnership:
        record = await get_domain_by_id(self._db, domain_id)
        if record is None:
            raise DomainNotFoundError
        if record.user_id != user_id:
            raise DomainForbiddenError
        return record

    async def verify(self, domain_id: int, user_id: int) -> DomainOwnership:
        record = await self.get_domain(domain_id, user_id)
        if record.is_verified:
            return record

        if record.verification_method == "file":
            await self._verify_file(record)
        else:
            await self._verify_dns(record)

        record.is_verified = True
        record.verified_at = datetime.now(timezone.utc)
        return record

    async def _verify_file(self, record: DomainOwnership) -> None:
        url = f"https://{record.domain}/webguard-verify-{record.verification_token}.txt"
        try:
            async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
                resp = await client.get(url)
        except httpx.RequestError as exc:
            raise DomainVerificationError(f"Network error reaching {url}: {exc}") from exc

        if resp.status_code != 200 or record.verification_token not in resp.text:
            raise DomainVerificationError(
                f"File not found or token mismatch at {url} (HTTP {resp.status_code})"
            )

    async def _verify_dns(self, record: DomainOwnership) -> None:
        expected = f"webguard-verify={record.verification_token}"
        name = f"_webguard.{record.domain}"
        try:
            answers = await dns.asyncresolver.resolve(name, "TXT")
        except Exception as exc:
            raise DomainVerificationError(f"DNS lookup failed for {name}: {exc}") from exc

        for rdata in answers:
            for txt_bytes in rdata.strings:
                if txt_bytes.decode() == expected:
                    return

        raise DomainVerificationError(
            f'TXT record not found: {name} must contain "{expected}"'
        )
