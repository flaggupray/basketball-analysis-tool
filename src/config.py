"""Encrypted API key storage using Fernet (AES-128-CBC).

The encryption key is derived from machine identifiers so it only
works on the same computer. Never commit the config to git.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import platform
import uuid
from pathlib import Path

from cryptography.fernet import Fernet


CONFIG_DIR = Path.home() / ".basketball-analyzer"
CONFIG_FILE = CONFIG_DIR / "config.enc"
KEY_FILE = CONFIG_DIR / ".key"


def _derive_key() -> bytes:
    """Derive a 32-byte Fernet key from machine identifiers."""
    seed = (
        f"{uuid.getnode()}:{platform.node()}:{platform.machine()}:"
        f"{os.environ.get('USER', 'unknown')}:basketball-analyzer-salt"
    )
    digest = hashlib.sha256(seed.encode()).digest()
    return base64.urlsafe_b64encode(digest)


def _get_fernet() -> Fernet:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    if KEY_FILE.exists():
        key = KEY_FILE.read_bytes()
    else:
        key = _derive_key()
        KEY_FILE.write_bytes(key)
        KEY_FILE.chmod(0o600)

    return Fernet(key)


def save_api_key(api_key: str):
    """Encrypt and persist the API key."""
    f = _get_fernet()
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    encrypted = f.encrypt(api_key.encode())
    CONFIG_FILE.write_bytes(encrypted)
    CONFIG_FILE.chmod(0o600)


def load_api_key() -> str | None:
    """Decrypt and return the stored API key, or None."""
    if not CONFIG_FILE.exists():
        return None
    try:
        f = _get_fernet()
        return f.decrypt(CONFIG_FILE.read_bytes()).decode()
    except Exception:
        return None


def clear_api_key():
    """Remove stored API key."""
    for p in [CONFIG_FILE, KEY_FILE]:
        if p.exists():
            p.unlink()


def has_api_key() -> bool:
    return CONFIG_FILE.exists() and load_api_key() is not None
