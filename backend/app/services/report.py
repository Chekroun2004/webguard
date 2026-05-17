"""
ReportService — builds JSON and PDF reports from a completed scan.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.db.models.scan import Scan, Vulnerability


def generate_json_report(scan: Scan, findings: list[Vulnerability]) -> dict:
    severity_order = ("critical", "high", "medium", "low", "info")
    counts: dict[str, int] = {s: 0 for s in severity_order}
    for f in findings:
        if f.severity in counts:
            counts[f.severity] += 1

    return {
        "scan_id": scan.id,
        "url": str(scan.url),
        "status": scan.status,
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": {"total": len(findings), **counts},
        "findings": [
            {
                "name": f.name,
                "severity": f.severity,
                "description": f.description,
                "recommendation": f.recommendation,
                "evidence": f.evidence or "",
            }
            for f in sorted(
                findings,
                key=lambda x: (
                    severity_order.index(x.severity) if x.severity in severity_order else 99
                ),
            )
        ],
    }
