"""Lost↔Found matching. Embeddings for text similarity, rules for the rest.

Falls back to keyword baseline (`_baseline.calculate_match`) on any failure.
Image similarity intentionally remains unavailable: image presence must never
be presented as visual similarity when no image model is configured.
"""

from __future__ import annotations

from loguru import logger

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
    try:
        text_score = await client.text_similarity_score(lost_text, found_text)
    except Exception:
        logger.exception("[ai:50002] match text model failed unexpectedly")
        return _baseline.calculate_match(req)
    if text_score is None:
        return _baseline.calculate_match(req)

    image_score = 0.0
    location_score = _baseline.location_score_value(req.lost_item.location, req.found_item.location)
    time_score = _baseline.time_score_value(
        req.lost_item.time,
        req.found_item.time,
        req.lost_item.time_end,
    )
    total = _baseline.normalized_total(
        req,
        image_score=image_score,
        text_score=text_score,
        location_score=location_score,
        time_score=time_score,
        image_available=False,
    )

    return CalculateMatchResponse(
        image_score=round(image_score, 2),
        text_score=round(text_score, 2),
        location_score=round(location_score, 2),
        time_score=round(time_score, 2),
        total_score=round(total, 2),
        image_available=False,
        degraded=True,
        score_source="TEXT_MODEL_RULES",
    )


def _doc(name: str | None, description: str | None) -> str:
    parts = [p.strip() for p in (name, description) if p and p.strip()]
    return " ".join(parts)
