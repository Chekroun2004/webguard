"""
SslTlsScanner — checks SSL/TLS protocol version and certificate validity.

Flags: TLS < 1.2, certificate expiring within 90 days, SSL errors.
"""

from __future__ import annotations

import asyncio
import ssl
from datetime import UTC, datetime
from urllib.parse import urlparse

from app.scanners.base import BaseScanner, Finding

OUTDATED_VERSIONS = {"TLSv1", "TLSv1.1", "SSLv2", "SSLv3"}
EXPIRY_FMT = "%b %d %H:%M:%S %Y %Z"


class SslTlsScanner(BaseScanner):
    async def _ssl_info(self, hostname: str, port: int = 443) -> dict:
        ctx = ssl.create_default_context()
        try:
            _, writer = await asyncio.open_connection(
                hostname, port, ssl=ctx, server_hostname=hostname
            )
            ssl_obj = writer.get_extra_info("ssl_object")
            version = ssl_obj.version() if ssl_obj else None
            cert = ssl_obj.getpeercert() if ssl_obj else None
            writer.close()
            await writer.wait_closed()
            return {"version": version, "cert": cert, "error": None}
        except ssl.SSLError as exc:
            return {"version": None, "cert": None, "error": str(exc.reason or exc)}
        except OSError as exc:
            return {"version": None, "cert": None, "error": str(exc)}

    async def scan(self, url: str, config: dict) -> list[Finding]:
        parsed = urlparse(url)
        hostname = parsed.hostname or ""
        port = parsed.port or (443 if parsed.scheme == "https" else 80)

        info = await self._ssl_info(hostname, port)
        findings: list[Finding] = []

        if info["error"]:
            findings.append(
                Finding(
                    name="SSL/TLS Error",
                    severity="high",
                    description="An SSL/TLS error occurred while connecting to the server.",
                    recommendation="Ensure the server has a valid, trusted SSL certificate.",
                    evidence=info["error"],
                )
            )
            return findings

        version: str | None = info["version"]
        if version and version in OUTDATED_VERSIONS:
            findings.append(
                Finding(
                    name="Outdated TLS Version",
                    severity="high",
                    description=f"The server supports {version}, which is deprecated and insecure.",
                    recommendation="Disable TLS 1.0 and 1.1; support only TLS 1.2 and 1.3.",
                    evidence=version,
                )
            )

        cert = info["cert"]
        if cert:
            findings.extend(self._check_expiry(cert))

        return findings

    def _check_expiry(self, cert: dict) -> list[Finding]:
        not_after = cert.get("notAfter", "")
        if not not_after:
            return []
        try:
            expiry = datetime.strptime(not_after, EXPIRY_FMT).replace(tzinfo=UTC)
        except ValueError:
            return []

        now = datetime.now(UTC)
        days_left = (expiry - now).days

        if days_left <= 30:
            return [
                Finding(
                    name="Certificate Expiring Soon",
                    severity="high",
                    description=f"The SSL certificate expires in {days_left} days.",
                    recommendation="Renew the certificate immediately.",
                    evidence=not_after,
                )
            ]
        if days_left <= 90:
            return [
                Finding(
                    name="Certificate Expiring Soon",
                    severity="medium",
                    description=f"The SSL certificate expires in {days_left} days.",
                    recommendation="Plan to renew the certificate before it expires.",
                    evidence=not_after,
                )
            ]
        return []
