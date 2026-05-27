from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, HttpUrl

WebhookProvider = Literal["slack", "discord"]


class WebhookCreate(BaseModel):
    url: HttpUrl
    provider: WebhookProvider
    is_active: bool = True


class WebhookUpdate(BaseModel):
    url: HttpUrl | None = None
    provider: WebhookProvider | None = None
    is_active: bool | None = None


class WebhookOut(BaseModel):
    id: int
    url: str
    provider: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
