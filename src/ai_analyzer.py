"""AI analyzer — works with any OpenAI-compatible provider.

Presets for OpenAI, MiniMax, Groq, DeepSeek, Ollama, Together.
MiniMax uses their native v2 format; all others use /v1/chat/completions.
"""

from __future__ import annotations

import json, threading
from pathlib import Path
from typing import Any

import requests
from src.config import load, has_key, PROVIDERS, MODEL_DEFAULTS


def _cfg() -> dict:
    c = load()
    return {
        "key": c.get("key", ""),
        "base_url": c.get("base_url", PROVIDERS["MiniMax"]),
        "model": c.get("model", MODEL_DEFAULTS["MiniMax"]),
    }


def _is_minimax(url: str) -> bool:
    return "minimax.chat" in url


def _chat(prompt: str, max_tokens: int = 600, timeout: int = 25) -> dict:
    """Send a chat request using the configured provider."""
    c = _cfg()
    if not c["key"]: return {"error": "No API key configured."}

    headers = {"Authorization": f"Bearer {c['key']}", "Content-Type": "application/json"}

    if _is_minimax(c["base_url"]):
        # MiniMax native v2 format
        body = {
            "model": c["model"],
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
        }
    else:
        # OpenAI-compatible format
        body = {
            "model": c["model"],
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.7,
        }

    try:
        resp = requests.post(c["base_url"], headers=headers, json=body, timeout=timeout)
        if resp.status_code != 200:
            return {"error": f"HTTP {resp.status_code}: {resp.text[:200]}"}
        data = resp.json()

        if _is_minimax(c["base_url"]):
            err = (data.get("base_resp") or {}).get("status_msg", "")
            if err: return {"error": err}
            msg = data.get("choices", [{}])[0].get("message", {})
            content = msg.get("content") or msg.get("reasoning_content") or ""
        else:
            err = (data.get("error") or {}).get("message", "")
            if err: return {"error": err}
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

        return {"analysis": content, "model": c["model"]}
    except requests.RequestException as e:
        return {"error": f"Network: {e}"}


def analyze_shooting(shot_data: dict, player_name: str = "Player", frames=None) -> dict:
    if not has_key(): return {"error": "No API key configured."}
    makes = shot_data.get("makes", 0); misses = shot_data.get("misses", 0)
    total = makes + misses
    pct = makes / total if total else 0
    angle = shot_data.get("avg_release_angle")
    ang_std = shot_data.get("angle_consistency_std")

    prompt = (
        f"You are a basketball shooting coach. Analyze this session:\n\n"
        f"Player: {player_name}\n"
        f"Shots: {makes}M / {misses}X = {pct:.0%} ({total} total)\n"
        f"Grade: {shot_data.get('shooting_grade', 'N/A')}\n"
    )
    if angle is not None:
        prompt += f"Release Angle: {angle:.1f}° ({shot_data.get('angle_grade', 'N/A')})\n"
    if ang_std is not None:
        prompt += f"Consistency σ: {ang_std:.1f}° ({shot_data.get('consistency_grade', 'N/A')})\n"
    prompt += (
        "\nProvide:\n"
        "1. Overall assessment (1-2 sentences)\n"
        "2. What's working well\n"
        "3. What to improve\n"
        "4. One specific drill\n"
        "5. Motivational close\n"
        "Keep it under 250 words."
    )
    return _chat(prompt, 500)


def analyze_player_stats(player_data: dict) -> dict:
    if not has_key(): return {"error": "No API key configured."}
    prompt = (
        f"You are a basketball skills trainer. Player:\n"
        f"  Name: {player_data.get('name', 'N/A')}\n"
        f"  Position: {player_data.get('position', 'N/A')}\n"
        f"  Level: {player_data.get('level', 'N/A')}\n"
        f"  Stats: {json.dumps(player_data.get('stats', {}))}\n"
        f"  Top weaknesses: {json.dumps(player_data.get('weaknesses', []))}\n\n"
        f"Give: 1) a 1-sentence diagnosis, 2) a 3-drill weekly plan, 3) a mindset tip.\n"
        f"Keep under 200 words."
    )
    return _chat(prompt, 400)


def test_connection(key: str = "", base_url: str = "", model: str = "") -> dict:
    """Test connectivity with given or stored credentials."""
    c = _cfg()
    key = key or c["key"]
    base_url = base_url or c["base_url"]
    model = model or c["model"]
    if not key: return {"ok": False, "error": "No API key"}

    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    body = {"model": model, "messages": [{"role": "user", "content": "Say OK"}], "max_tokens": 5}

    if _is_minimax(base_url):
        # MiniMax uses their own format — test with empty prompt to check auth
        pass  # body already set above

    try:
        resp = requests.post(base_url, headers=headers, json=body, timeout=12)
        data = resp.json()

        if _is_minimax(base_url):
            code = (data.get("base_resp") or {}).get("status_code", 0)
            if code == 0 and data.get("choices"):
                return {"ok": True, "model": model}
            err = (data.get("base_resp") or {}).get("status_msg", f"HTTP {resp.status_code}")
            return {"ok": False, "error": err}
        else:
            if "choices" in data and data["choices"]:
                return {"ok": True, "model": model}
            err = (data.get("error") or {}).get("message", f"HTTP {resp.status_code}")
            return {"ok": False, "error": err}
    except Exception as e:
        return {"ok": False, "error": str(e)}
