from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, HttpUrl


class ScheduledScanCreate(BaseModel):
    url: HttpUrl
    cron_expression: str
    is_active: bool = True


class ScheduledScanUpdate(BaseModel):
    cron_expression: str | None = None
    is_active: bool | None = None


class ScheduledScanOut(BaseModel):
    id: int
    url: str
    cron_expression: str
    is_active: bool
    last_run_at: datetime | None
    next_run_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}
