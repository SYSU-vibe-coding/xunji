"""Lost↔Found matching. Embeddings for text similarity, rules for the rest.

Falls back to keyword baseline (`_baseline.calculate_match`) on any failure.
Image similarity intentionally skipped in DashScope path: enabling it would
require multimodal-embedding which charges per call and isn't always
available in the user's region. The rule-based image score is kept.
"""

from __future__ import annotations

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

    # Use the high-level similarity scorer (chat-based or embedding-based
    # depending on which model env vars are set).
    text_score = await client.text_similarity_score(
        lost_text,
        found_text,
        lost_location=req.lost_item.location,
        found_location=req.found_item.location,
        lost_time=req.lost_item.time,
        found_time=req.found_item.time,
    )
    if text_score is None:
        return _baseline.calculate_match(req)

    image_score = _baseline.image_score_value(req.lost_item.image_urls, req.found_item.image_urls)
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
