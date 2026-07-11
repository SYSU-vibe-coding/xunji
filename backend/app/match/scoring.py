"""Rule-based scoring used when ai-service is unavailable.

Mirrors ``docs/architecture/matching-rules.md §2``. Inputs are the same
``{name, description, location, time, timeEnd, imageUrls}`` payloads that the
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


def rule_based_score(lost: dict[str, Any], found: dict[str, Any]) -> dict[str, Any]:
    """Return image/text/location/time/total scores (0-100)."""
    image = 0.0
    text = _text_score(
        _combine(lost.get("name"), lost.get("description")),
        _combine(found.get("name"), found.get("description")),
    )
    location = _location_score(lost.get("location"), found.get("location"))
    time = _time_score(lost.get("time"), found.get("time"), lost.get("timeEnd"))
    total = normalized_total(
        lost,
        found,
        image_score=image,
        text_score=text,
        location_score=location,
        time_score=time,
        image_available=False,
    )
    return {
        "imageScore": round(image, 2),
        "textScore": round(text, 2),
        "locationScore": round(location, 2),
        "timeScore": round(time, 2),
        "totalScore": round(total, 2),
        "imageAvailable": False,
        "degraded": True,
        "scoreSource": "RULE_BASED",
    }


def _image_score(left: list[str] | None, right: list[str] | None) -> float:
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
    # Containment (e.g. "图书馆二楼" ⊃ "图书馆") is a strong signal.
    if left in right or right in left:
        return 85.0
    return 60.0 if left[:2] == right[:2] else 0.0


def _time_score(
    lost_start: str | None,
    found_time: str | None,
    lost_end: str | None = None,
) -> float:
    if not lost_start or not found_time:
        return 0.0
    parsed: list[datetime] = []
    for raw in (lost_start, lost_end or lost_start, found_time):
        try:
            parsed.append(datetime.fromisoformat(raw.replace("Z", "+00:00")))
        except ValueError:
            return 0.0
    start, end, found = parsed
    try:
        if end < start:
            return 0.0
        if found < start:
            delta_hours = (start - found).total_seconds() / 3600.0
        elif found > end:
            delta_hours = (found - end).total_seconds() / 3600.0
        else:
            delta_hours = 0.0
    except TypeError:
        return 0.0
    return max(0.0, 100.0 - delta_hours * 2.0)


def normalized_total(
    lost: dict[str, Any],
    found: dict[str, Any],
    *,
    image_score: float,
    text_score: float,
    location_score: float,
    time_score: float,
    image_available: bool,
) -> float:
    """Calculate a weighted average over dimensions with usable signals."""
    weighted = 0.0
    available_weight = 0.0
    if image_available and lost.get("imageUrls") and found.get("imageUrls"):
        weighted += image_score * WEIGHT_IMAGE
        available_weight += WEIGHT_IMAGE
    if (
        _combine(lost.get("name"), lost.get("description")).strip()
        and _combine(found.get("name"), found.get("description")).strip()
    ):
        weighted += text_score * WEIGHT_TEXT
        available_weight += WEIGHT_TEXT
    if lost.get("location") and found.get("location"):
        weighted += location_score * WEIGHT_LOCATION
        available_weight += WEIGHT_LOCATION
    if lost.get("time") and found.get("time"):
        weighted += time_score * WEIGHT_TIME
        available_weight += WEIGHT_TIME
    return weighted / available_weight if available_weight else 0.0


def _combine(*parts: str | None) -> str:
    return " ".join(p for p in parts if p)


def _tokens(text: str) -> set[str]:
    return {t for t in re.split(r"\W+", text.lower()) if t}
