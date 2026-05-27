"""
Authenticated scan support — turns a stored auth_config into a cookie dict the
scanners can pass to ``httpx.AsyncClient(cookies=...)``.

Two strategies:
    cookie       → user-supplied session cookie (name + value)
    form_login   → POST credentials to login_url, capture Set-Cookie headers

Failures are logged and yield an empty cookie dict — the scan continues
unauthenticated rather than aborting.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


async def prepare_auth_cookies(auth_config: dict[str, Any] | None) -> dict[str, str]:
    if not auth_config:
        return {}

    strategy = auth_config.get("strategy")

    if strategy == "cookie":
        name = auth_config.get("name")
        value = auth_config.get("value")
        if not name or value is None:
            logger.warning("Cookie auth_config missing name/value")
            return {}
        return {name: value}

    if strategy == "form_login":
        return await _login_form(auth_config)

    logger.warning("Unknown auth strategy: %s", strategy)
    return {}


async def _login_form(cfg: dict[str, Any]) -> dict[str, str]:
    login_url = cfg.get("login_url")
    if not login_url:
        return {}
    payload = {
        cfg.get("username_field", "username"): cfg.get("username", ""),
        cfg.get("password_field", "password"): cfg.get("password", ""),
    }
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
            response = await client.post(login_url, data=payload)
            response.raise_for_status()
            return {k: v for k, v in client.cookies.items()}
    except Exception as exc:
        logger.warning("form_login to %s failed: %s", login_url, exc)
        return {}
