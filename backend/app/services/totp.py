"""
TOTP (RFC 6238) helpers — secret generation, otpauth URI build, code verification.

The secret is generated server-side, stored encrypted via app.core.crypto, and
returned in plaintext exactly once (during enrollment) so the user can scan it
into Google Authenticator / 1Password / etc.
"""

from __future__ import annotations

from urllib.parse import quote

import pyotp

ISSUER = "WebGuard"


def generate_secret() -> str:
    """Generate a fresh base32 TOTP secret (160 bits)."""
    return pyotp.random_base32()


def build_otpauth_uri(secret: str, account: str) -> str:
    """Build the otpauth:// URI a TOTP app encodes as a QR code."""
    account_label = quote(f"{ISSUER}:{account}", safe="")
    issuer = quote(ISSUER, safe="")
    return f"otpauth://totp/{account_label}?secret={secret}&issuer={issuer}&digits=6&period=30"


def verify_code(secret: str, code: str, *, valid_window: int = 1) -> bool:
    """Return True if *code* matches the current TOTP for *secret*.

    ``valid_window`` allows ±N 30s steps to absorb clock skew (default ±1).
    """
    if not code or not code.isdigit():
        return False
    return bool(pyotp.TOTP(secret).verify(code, valid_window=valid_window))
