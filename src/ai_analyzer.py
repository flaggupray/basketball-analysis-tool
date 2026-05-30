"""MiniMax AI analyzer for basketball shooting video feedback.

Uses the fastest MiniMax chat model to provide coaching analysis
based on shot tracking data extracted from video.
"""

from __future__ import annotations

import base64
import json
from io import BytesIO
from pathlib import Path
from typing import Any

import numpy as np
import requests
from PIL import Image

from src.config import load_api_key, has_api_key

MINIMAX_BASE = "https://api.minimax.chat/v1"
DEFAULT_MODEL = "abab6.5s-chat"
FALLBACK_MODELS = ["abab6.5s-chat", "abab6.5-chat", "abab6-chat", "abab5.5s-chat", "MiniMax-Text-01"]

_MODEL_CACHE: str | None = None


def _model_config_path() -> Path:
    p = Path.home() / ".basketball-analyzer" / ".model"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p

def get_model() -> str:
    global _MODEL_CACHE
    if _MODEL_CACHE:
        return _MODEL_CACHE
    p = _model_config_path()
    if p.exists():
        _MODEL_CACHE = p.read_text().strip()
        return _MODEL_CACHE
    return DEFAULT_MODEL

def save_model(model: str):
    global _MODEL_CACHE
    _MODEL_CACHE = model
    p = _model_config_path()
    p.write_text(model)

def get_available_models() -> list[str]:
    return FALLBACK_MODELS


def _headers() -> dict[str, str]:
    key = load_api_key()
    if not key:
        raise RuntimeError("API key not configured")
    return {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


def _encode_frame(frame: np.ndarray) -> str:
    """Convert a numpy RGB frame to base64 JPEG for the API."""
    img = Image.fromarray(frame)
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=75)
    return base64.b64encode(buf.getvalue()).decode()


def analyze_shooting(
    shot_data: dict,
    frames: list[np.ndarray] | None = None,
    player_name: str = "Player",
) -> dict[str, Any]:
    """Send shot tracking data to MiniMax for AI coaching analysis.

    Args:
        shot_data: Dict with makes, misses, angles, consistency stats
        frames: Optional key frames from the video
        player_name: Player name for personalized feedback
    """
    if not has_api_key():
        return {"error": "API key not configured. Set it in Settings tab."}

    # Build prompt
    prompt = _build_shooting_prompt(shot_data, player_name)
    messages = [{"role": "user", "content": prompt}]

    # If frames provided, add as image content
    if frames and len(frames) > 0:
        content_parts = []
        # Add up to 3 key frames
        for i, frame in enumerate(frames[:3]):
            b64 = _encode_frame(frame)
            content_parts.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
            })
        content_parts.append({"type": "text", "text": prompt})
        messages = [{"role": "user", "content": content_parts}]

    try:
        model = get_model()
        resp = requests.post(
            f"{MINIMAX_BASE}/text/chatcompletion_v2",
            headers=_headers(),
            json={
                "model": model,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 800,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

        if data.get("base_resp", {}).get("status_code") != 0:
            return {"error": data.get("base_resp", {}).get("status_msg", "API error")}

        reply = data["choices"][0]["message"]["content"]

        return {
            "analysis": reply,
            "model": model,
            "tokens_used": data.get("usage", {}).get("total_tokens", 0),
        }

    except requests.RequestException as e:
        return {"error": f"Network error: {str(e)}"}
    except (KeyError, IndexError) as e:
        return {"error": f"Unexpected API response: {str(e)}"}


def _build_shooting_prompt(shot_data: dict, name: str) -> str:
    """Build a structured prompt for the AI coach."""
    makes = shot_data.get("makes", 0)
    misses = shot_data.get("misses", 0)
    total = makes + misses
    make_pct = makes / total if total > 0 else 0

    angle = shot_data.get("avg_release_angle")
    angle_std = shot_data.get("angle_consistency_std")
    consistency = shot_data.get("consistency_grade", "N/A")
    angle_grade = shot_data.get("angle_grade", "N/A")
    shooting_grade = shot_data.get("shooting_grade", "N/A")

    prompt = f"""You are a professional basketball shooting coach. Analyze this player's shooting session data and give personalized, actionable feedback. Be encouraging but honest. Keep it under 300 words.

Player: {name}
Shots: {makes} makes / {misses} misses = {make_pct:.0%} ({total} total)
Shooting Grade: {shooting_grade}
"""

    if angle is not None:
        prompt += f"Average Release Angle: {angle:.1f}° ({angle_grade})\n"

    if angle_std is not None:
        prompt += f"Angle Consistency (std dev): {angle_std:.1f}° ({consistency})\n"

    prompt += """
Please provide:
1. **Overall Assessment** — 1-2 sentences on their shooting performance
2. **What's Working** — 1-2 things they're doing well
3. **What to Improve** — 1-2 specific areas to focus on
4. **Drill Recommendation** — 1 specific drill to practice
5. **Encouragement** — a motivational closing line

Format the response in Chinese if the player name appears to be Chinese, otherwise English."""
    return prompt


def analyze_player_stats(
    player_data: dict,
) -> dict[str, Any]:
    """AI analysis of player stat weaknesses for additional coaching insight."""
    if not has_api_key():
        return {"error": "API key not configured."}

    prompt = f"""You are a basketball skills trainer. A player has the following stats and identified weaknesses. Give a concise training plan.

Player: {player_data.get('name', 'Unknown')}
Position: {player_data.get('position', 'N/A')}
Level: {player_data.get('level', 'N/A')}

Stats:
{json.dumps(player_data.get('stats', {}), indent=2)}

Top 3 Weaknesses:
{json.dumps(player_data.get('weaknesses', []), indent=2)}

Provide:
1. A 2-sentence summary of their biggest issue
2. A 3-drill weekly training plan targeting their weaknesses
3. A mindset tip for improvement

Keep the response under 250 words. Be direct and specific."""

    try:
        resp = requests.post(
            f"{MINIMAX_BASE}/text/chatcompletion_v2",
            headers=_headers(),
            json={
                "model": get_model(),
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 600,
            },
            timeout=25,
        )
        resp.raise_for_status()
        data = resp.json()

        if data.get("base_resp", {}).get("status_code") != 0:
            return {"error": data.get("base_resp", {}).get("status_msg", "API error")}

        return {
            "analysis": data["choices"][0]["message"]["content"],
            "model": get_model(),
        }

    except requests.RequestException as e:
        return {"error": f"Network error: {str(e)}"}
    except (KeyError, IndexError) as e:
        return {"error": f"Unexpected API response: {str(e)}"}


def test_connection() -> dict[str, Any]:
    """Quick test that the API key works, trying fallback models."""
    if not has_api_key():
        return {"ok": False, "error": "No API key configured"}

    models_to_try = [get_model()] + [m for m in FALLBACK_MODELS if m != get_model()]

    for model in models_to_try:
        try:
            resp = requests.post(
                f"{MINIMAX_BASE}/text/chatcompletion_v2",
                headers=_headers(),
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": "Say OK"}],
                    "max_tokens": 10,
                },
                timeout=10,
            )
            data = resp.json()
            base = data.get("base_resp", {})
            code = base.get("status_code", 0)
            if code == 0 and data.get("choices"):
                save_model(model)
                return {"ok": True, "model": model}
            elif code == 0 and data.get("choices") is not None:
                save_model(model)
                return {"ok": True, "model": model}
        except Exception:
            continue

    return {"ok": False, "error": "No working model found for this API plan. Set model manually in Settings."}
