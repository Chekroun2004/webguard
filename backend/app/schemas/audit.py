"""Pydantic schemas for audit events."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

AuditAction = Literal[
    "scan.create",
    "scan.delete",
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
]

AuditStatus = Literal["success", "failure"]


class AuditEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    action: str
    target_type: str | None
    target_id: int | None
    status: str
    ip: str | None
    user_agent: str | None
    created_at: datetime


class AuditEventList(BaseModel):
    items: list[AuditEventOut]
    total: int
    page: int
    page_size: int
