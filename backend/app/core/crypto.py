"""
Symmetric encryption for sensitive payloads stored in the database (e.g. scan
auth credentials).

The Fernet key is derived from ``settings.secret_key`` via HKDF so we don't
require an extra environment variable. Rotating ``SECRET_KEY`` therefore
invalidates every previously encrypted blob — acceptable for this project,
documented in CLAUDE.md.
"""

from __future__ import annotations

import base64
import json
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from app.core.config import settings

_HKDF_INFO = b"webguard.scan-auth-config.v1"
_HKDF_SALT = b"webguard.scan-auth-config.salt.v1"


def _derive_fernet_key(secret: str) -> bytes:
    raw = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=_HKDF_SALT,
        info=_HKDF_INFO,
    ).derive(secret.encode("utf-8"))
    return base64.urlsafe_b64encode(raw)


_fernet = Fernet(_derive_fernet_key(settings.secret_key))


class DecryptionError(Exception):
    """Raised when ciphertext cannot be decrypted (tampered or wrong key)."""


def encrypt_json(payload: dict[str, Any]) -> str:
    return _fernet.encrypt(json.dumps(payload).encode("utf-8")).decode("ascii")


def decrypt_json(ciphertext: str) -> dict[str, Any]:
    try:
        plaintext = _fernet.decrypt(ciphertext.encode("ascii"))
    except InvalidToken as exc:
        raise DecryptionError("Invalid or tampered ciphertext") from exc
    return json.loads(plaintext.decode("utf-8"))
