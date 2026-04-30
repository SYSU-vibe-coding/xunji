"""Rule-based scoring used when ai-service is unavailable.

Mirrors ``docs/architecture/matching-rules.md §2``. Inputs are the same
``{name, description, location, time, imageUrls}`` payloads that the
ai-service contract uses, so callers can transparently switch between this
function and the real AI response.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

# Match the weights from matching-rules.md §1
WEIGHT_IMAGE = 0.4
WEIGHT_TEXT = 0.3
WEIGHT_LOCATION = 0.2
WEIGHT_TIME = 0.1


def rule_based_score(lost: dict[str, Any], found: dict[str, Any]) -> dict[str, float]:
    """Return image/text/location/time/total scores (0-100)."""
    image = _image_score(lost.get("imageUrls"), found.get("imageUrls"))
    text = _text_score(
        _combine(lost.get("name"), lost.get("description")),
        _combine(found.get("name"), found.get("description")),
    )
    location = _location_score(lost.get("location"), found.get("location"))
    time = _time_score(lost.get("time"), found.get("time"))
    total = (
        image * WEIGHT_IMAGE + text * WEIGHT_TEXT + location * WEIGHT_LOCATION + time * WEIGHT_TIME
    )
    return {
        "imageScore": round(image, 2),
        "textScore": round(text, 2),
        "locationScore": round(location, 2),
        "timeScore": round(time, 2),
        "totalScore": round(total, 2),
    }


def _image_score(left: list[str] | None, right: list[str] | None) -> float:
    # Without AI we have no real image similarity. Per matching-rules.md §2
    # this is simply 0; we keep a small bonus when both sides have images so
    # equally-described items don't end up identical to the no-image case.
    if left and right:
        return 30.0
    return 0.0


def _text_score(left: str, right: str) -> float:
    left_tokens = _tokens(left)
    right_tokens = _tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens) * 100.0


def _location_score(left: str | None, right: str | None) -> float:
    if not left or not right:
        return 0.0
    if left == right:
        return 100.0
    return 60.0 if left[:2] == right[:2] else 0.0


def _time_score(left: str | None, right: str | None) -> float:
    if not left or not right:
        return 0.0
    parsed: list[datetime] = []
    for raw in (left, right):
        try:
            parsed.append(datetime.fromisoformat(raw.replace("Z", "+00:00")))
        except ValueError:
            return 50.0
    delta_hours = abs((parsed[0] - parsed[1]).total_seconds()) / 3600.0
    return max(0.0, 100.0 - delta_hours * 2.0)


def _combine(*parts: str | None) -> str:
    return " ".join(p for p in parts if p)


def _tokens(text: str) -> set[str]:
    return {t for t in re.split(r"\W+", text.lower()) if t}
