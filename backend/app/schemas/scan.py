"""
Pydantic v2 schemas for Scan and Vulnerability.
"""
from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import AnyHttpUrl, BaseModel, Field


# ── Request ──────────────────────────────────────────────────────────────────

class ScanCreate(BaseModel):
    url: AnyHttpUrl


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
