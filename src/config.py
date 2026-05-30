"""Encrypted provider config — API key, base URL, model.

Never committed to git. Fernet encryption keyed to this machine.
"""

from __future__ import annotations

import base64, hashlib, json, os, platform, uuid
from pathlib import Path
from cryptography.fernet import Fernet

CONFIG_DIR = Path.home() / ".basketball-analyzer"
_FILE = CONFIG_DIR / "config.enc"
_KEY_FILE = CONFIG_DIR / ".key"

# ── presets ────────────────────────────────────────────────────

PROVIDERS = {
    "OpenAI":      "https://api.openai.com/v1",
    "MiniMax":     "https://api.minimax.chat/v1/text/chatcompletion_v2",
    "Groq":        "https://api.groq.com/openai/v1",
    "DeepSeek":    "https://api.deepseek.com/v1",
    "Ollama":      "http://localhost:11434/v1",
    "Together":    "https://api.together.xyz/v1",
    "Custom":      "",
}
MODEL_DEFAULTS = {
    "OpenAI":   "gpt-4o-mini",
    "MiniMax":  "MiniMax-M2.5-highspeed",
    "Groq":     "llama-3.3-70b-versatile",
    "DeepSeek": "deepseek-chat",
    "Ollama":   "llama3.2",
    "Together": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
    "Custom":   "",
}


def _fernet() -> Fernet:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if _KEY_FILE.exists():
        return Fernet(_KEY_FILE.read_bytes())
    seed = f"{uuid.getnode()}:{platform.node()}:basketball-salt"
    key = base64.urlsafe_b64encode(hashlib.sha256(seed.encode()).digest())
    _KEY_FILE.write_bytes(key); _KEY_FILE.chmod(0o600)
    return Fernet(key)


def _read() -> dict:
    if not _FILE.exists(): return {}
    try: return json.loads(_fernet().decrypt(_FILE.read_bytes()))
    except Exception: return {}


def _write(d: dict):
    _FILE.write_bytes(_fernet().encrypt(json.dumps(d).encode()))
    _FILE.chmod(0o600)


def save(key: str = "", base_url: str = "", model: str = ""):
    d = _read()
    if key: d["key"] = key
    if base_url: d["base_url"] = base_url
    if model: d["model"] = model
    _write(d)


def load() -> dict:
    """Return {key, base_url, model} or empty dict."""
    return _read()


def clear():
    for p in [_FILE, _KEY_FILE]:
        if p.exists(): p.unlink()

def has_key() -> bool:
    return bool(load().get("key"))
