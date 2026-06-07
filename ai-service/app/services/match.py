"""Lost↔Found matching. Embeddings for text similarity, rules for the rest.

Falls back to keyword baseline (`_baseline.calculate_match`) on any failure.
Image similarity intentionally skipped in DashScope path: enabling it would
require multimodal-embedding which charges per call and isn't always
available in the user's region. The rule-based image score (0/60) is kept.
"""

from __future__ import annotations

import math

from app.clients.dashscope import DashScopeClient
from app.schemas import CalculateMatchRequest, CalculateMatchResponse
from app.services import _baseline


async def calculate_match(
    req: CalculateMatchRequest, client: DashScopeClient | None
) -> CalculateMatchResponse:
    if client is None or not client.enabled:
        return _baseline.calculate_match(req)

    lost_text = _doc(req.lost_item.name, req.lost_item.description)
    found_text = _doc(req.found_item.name, req.found_item.description)
    if not lost_text or not found_text:
        return _baseline.calculate_match(req)

    vectors = await client.text_embedding([lost_text, found_text])
    if vectors is None or len(vectors) != 2:
        return _baseline.calculate_match(req)

    text_score = max(0.0, _cosine(vectors[0], vectors[1])) * 100.0

    image_score = 60.0 if req.lost_item.image_urls and req.found_item.image_urls else 0.0
    location_score = _baseline.location_score_value(req.lost_item.location, req.found_item.location)
    time_score = _baseline.time_score_value(req.lost_item.time, req.found_item.time)
    total = image_score * 0.4 + text_score * 0.3 + location_score * 0.2 + time_score * 0.1

    return CalculateMatchResponse(
        image_score=round(image_score, 2),
        text_score=round(text_score, 2),
        location_score=round(location_score, 2),
        time_score=round(time_score, 2),
        total_score=round(total, 2),
    )


def _doc(name: str | None, description: str | None) -> str:
    parts = [p.strip() for p in (name, description) if p and p.strip()]
    return " ".join(parts)


def _cosine(a: list[float], b: list[float]) -> float:
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
