"""Audit service — writes activity events without breaking business operations.

The log() method wraps the insert in a SAVEPOINT (db.begin_nested()) so that a
failure to write the audit row never rolls back the business transaction.
"""

from __future__ import annotations

import logging
from typing import Literal

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.audit_event import AuditEvent
from app.repositories.audit import create_audit_event

logger = logging.getLogger(__name__)

ACTIONS: frozenset[str] = frozenset({
    "scan.create",
    "scheduled.create",
    "scheduled.update",
    "scheduled.delete",
    "domain.create",
    "domain.delete",
    "api_key.create",
    "api_key.revoke",
    "webhook.create",
    "webhook.delete",
    "webhook.test",
    "totp.enable",
    "totp.disable",
})

UA_MAX_LEN = 512


class AuditService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def log(
        self,
        user_id: int,
        action: str,
        *,
        target_type: str | None = None,
        target_id: int | None = None,
        status: Literal["success", "failure"] = "success",
        request: Request | None = None,
    ) -> AuditEvent | None:
        if action not in ACTIONS:
            raise ValueError(f"unknown audit action: {action}")

        ip: str | None = None
        ua: str | None = None
        if request is not None:
            if request.client is not None:
                ip = request.client.host
            ua = request.headers.get("user-agent")
            if ua is not None and len(ua) > UA_MAX_LEN:
                ua = ua[:UA_MAX_LEN]

        try:
            async with self._db.begin_nested():
                event = await create_audit_event(
                    self._db,
                    user_id=user_id,
                    action=action,
                    target_type=target_type,
                    target_id=target_id,
                    status=status,
                    ip=ip,
                    user_agent=ua,
                )
            await self._db.flush()
            return event
        except Exception:  # pragma: no cover - defensive
            logger.warning(
                "audit_log_failed action=%s user_id=%s", action, user_id, exc_info=True
            )
            return None
