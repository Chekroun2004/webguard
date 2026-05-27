"""
Abstract base class for all WebGuard scanners.

Each scanner receives a URL + config dict and returns a list of Finding objects.
Subclasses must implement:
  - scan(url, config) -> list[Finding]
  - _fetch(url) -> dict  (overridable for testing)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Literal

import httpx

Severity = Literal["info", "low", "medium", "high", "critical"]


@dataclass
class Finding:
    name: str
    severity: Severity
    description: str
    recommendation: str = ""
    evidence: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


class BaseScanner(ABC):
    """Base class all scanners inherit from."""

    async def _fetch(self, url: str, cookies: dict[str, str] | None = None) -> dict:
        """Perform an HTTP GET and return a normalised response dict.

        Override in tests via patch.object(scanner, '_fetch', AsyncMock(...)).
        ``cookies`` allows authenticated scanners to reuse a session.
        """
        async with httpx.AsyncClient(
            follow_redirects=True, timeout=15, cookies=cookies or {}
        ) as client:
            resp = await client.get(url)
            return {
                "status": resp.status_code,
                "headers": dict(resp.headers),
                "body": resp.text,
            }

    @abstractmethod
    async def scan(self, url: str, config: dict) -> list[Finding]:
        """Run the scan and return findings."""
