"""
Pydantic v2 schemas for Scan and Vulnerability.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import AnyHttpUrl, BaseModel, Field

# ── Auth config ───────────────────────────────────────────────────────────────


class CookieAuthConfig(BaseModel):
    strategy: Literal["cookie"] = "cookie"
    name: str = Field(min_length=1, max_length=128)
    value: str = Field(min_length=1, max_length=4096)


class FormLoginAuthConfig(BaseModel):
    strategy: Literal["form_login"] = "form_login"
    login_url: AnyHttpUrl
    username_field: str = Field(min_length=1, max_length=128)
    password_field: str = Field(min_length=1, max_length=128)
    username: str = Field(min_length=1, max_length=256)
    password: str = Field(min_length=1, max_length=256)


AuthConfig = CookieAuthConfig | FormLoginAuthConfig


# ── Request ──────────────────────────────────────────────────────────────────


class ScanCreate(BaseModel):
    url: AnyHttpUrl
    auth_config: AuthConfig | None = Field(default=None, discriminator="strategy")


# ── Response fragments ────────────────────────────────────────────────────────


class VulnerabilityOut(BaseModel):
    id: int
    name: str
    severity: str
    description: str
    recommendation: str
    evidence: str

    model_config = {"from_attributes": True}


class ScanOut(BaseModel):
    id: int
    url: str
    status: str
    created_at: datetime
    finished_at: datetime | None = None
    findings: list[VulnerabilityOut] = Field(default_factory=list)

    model_config = {"from_attributes": True}
