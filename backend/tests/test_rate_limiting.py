"""
Integration tests for API rate limiting.

These tests explicitly re-enable the limiter (disabled globally by the
disable_rate_limiting autouse fixture in conftest.py).
"""

from unittest.mock import patch

import pytest


@pytest.mark.asyncio
async def test_scan_rate_limit_5_per_hour(client, auth_headers):
    """6th POST /scans within an hour must return 429."""
    from app.core.limiter import limiter

    limiter.enabled = True
    limiter._storage.reset()

    # Mock Celery dispatch — there is no broker in CI
    with patch("app.api.v1.scans.run_scan_task.delay"):
        try:
            for i in range(5):
                resp = await client.post(
                    "/api/v1/scans",
                    json={"url": "https://example.com"},
                    headers=auth_headers,
                )
                assert resp.status_code == 202, f"Call {i + 1} failed: {resp.text}"

            resp = await client.post(
                "/api/v1/scans",
                json={"url": "https://example.com"},
                headers=auth_headers,
            )
            assert resp.status_code == 429
        finally:
            limiter.enabled = False
            limiter._storage.reset()
