from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, field_validator


class DomainCreate(BaseModel):
    domain: str
    method: Literal["file", "dns"] = "file"

    @field_validator("domain")
    @classmethod
    def domain_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Domain cannot be empty")
        return v.strip()


class DomainOut(BaseModel):
    id: int
    domain: str
    verification_method: str
    verification_token: str
    is_verified: bool
    verified_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
