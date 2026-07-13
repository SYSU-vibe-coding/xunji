"""HTTP client for the standalone AI service.

Wraps the three internal endpoints documented in ``docs/api/ai-service.md``
and applies the 3-second timeout budget the document promises. Every method
returns ``None`` on failure (timeout, non-2xx, malformed payload). Callers
MUST treat ``None`` as "fall back" — no exception is propagated, so a
broken AI service never breaks a main-backend transaction.
"""

from __future__ import annotations

import math
from typing import Any

import httpx
from loguru import logger
from pydantic import ValidationError

from app.common.errors import ErrorCode
from app.core.config import settings
from app.match.scoring import normalized_total

MATCH_SCORE_SOURCES = {"RULE_BASED", "TEXT_MODEL_RULES", "MULTIMODAL_MODEL"}
ITEM_CATEGORIES = {"CERT", "ELECTRONIC", "DAILY_USE", "BOOK", "OTHER"}
ANSWER_VERIFY_SOURCES = {"KEYWORD_RULES", "TEXT_MODEL"}


class AIClient:
    """Async client for ai-service. One instance per process is enough."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        timeout: float | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._base_url = (base_url or settings.AI_SERVICE_BASE_URL).rstrip("/")
        self._timeout = timeout if timeout is not None else settings.AI_SERVICE_TIMEOUT
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=self._timeout,
            headers={"X-Service-Token": settings.AI_SERVICE_TOKEN},
            # Don't pick up host-level proxy env vars (e.g. socks://) which
            # httpx may not understand. Internal traffic stays on localhost.
            trust_env=False,
            transport=transport,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def calculate_match(
        self,
        *,
        lost: dict[str, Any],
        found: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Score one (lost, found) pair. Returns the JSON body or None."""
        data = await self._post(
            "/internal/ai/calculate-match",
            {"lostItem": lost, "foundItem": found},
            expected_keys=(
                "imageScore",
                "textScore",
                "locationScore",
                "timeScore",
                "totalScore",
                "imageAvailable",
                "degraded",
                "scoreSource",
            ),
        )
        if data is None:
            return None
        score_keys = ("imageScore", "textScore", "locationScore", "timeScore", "totalScore")
        scores: dict[str, float] = {}
        for key in score_keys:
            value = data[key]
            if isinstance(value, bool) or not isinstance(value, int | float):
                return None
            score = float(value)
            if not math.isfinite(score) or not 0 <= score <= 100:
                return None
            scores[key] = score
        image_available = data["imageAvailable"]
        degraded = data["degraded"]
        score_source = data["scoreSource"]
        if not isinstance(image_available, bool) or not isinstance(degraded, bool):
            return None
        if not isinstance(score_source, str) or score_source not in MATCH_SCORE_SOURCES:
            return None
        if image_available and (not lost.get("imageUrls") or not found.get("imageUrls")):
            return None
        if not image_available and scores["imageScore"] != 0:
            return None
        scores["totalScore"] = round(
            normalized_total(
                lost,
                found,
                image_score=scores["imageScore"],
                text_score=scores["textScore"],
                location_score=scores["locationScore"],
                time_score=scores["timeScore"],
                image_available=image_available,
            ),
            2,
        )
        return {
            **scores,
            "imageAvailable": image_available,
            "degraded": degraded,
            "scoreSource": score_source,
        }

    async def classify_item(
        self,
        *,
        image_urls: list[str] | None = None,
        item_name: str | None = None,
        description: str | None = None,
    ) -> dict[str, Any] | None:
        if not image_urls and not item_name:
            return None
        payload: dict[str, Any] = {}
        if image_urls:
            payload["imageUrls"] = image_urls
        if item_name:
            payload["itemName"] = item_name
        if description:
            payload["description"] = description
        data = await self._post(
            "/internal/ai/classify-item",
            payload,
            expected_keys=("category", "tags", "confidence", "degraded", "source"),
        )
        if data is None:
            return None
        category = data["category"]
        tags = data["tags"]
        confidence = data["confidence"]
        if (
            not isinstance(category, str)
            or category not in ITEM_CATEGORIES
            or not isinstance(tags, list)
            or len(tags) > 10
        ):
            return None
        if any(
            not isinstance(tag, str) or not tag.strip() or len(tag.strip()) > 20 for tag in tags
        ):
            return None
        if (
            isinstance(confidence, bool)
            or not isinstance(confidence, int | float)
            or not math.isfinite(float(confidence))
            or not 0 <= float(confidence) <= 100
        ):
            return None
        source = data["source"]
        if (
            not isinstance(data["degraded"], bool)
            or not isinstance(source, str)
            or source not in {"KEYWORD_RULES", "VISION_MODEL"}
        ):
            return None
        return data

    async def detect_sensitive(self, image_url: str) -> dict[str, Any] | None:
        if not image_url:
            return None
        return await self._post(
            "/internal/ai/detect-sensitive",
            {"imageUrl": image_url},
            expected_keys=("isSensitive",),
        )

    async def verify_claim_answers(self, answers: list[dict[str, Any]]) -> dict[str, Any] | None:
        if not 1 <= len(answers) <= 3:
            return None
        data = await self._post(
            "/internal/ai/verify-claim-answers",
            {"answers": answers},
            expected_keys=("scores", "passed", "degraded", "source"),
        )
        if data is None:
            return None
        scores = data["scores"]
        if not isinstance(scores, list) or len(scores) != len(answers):
            return None
        normalized_scores: list[float] = []
        for value in scores:
            if (
                isinstance(value, bool)
                or not isinstance(value, int | float)
                or not math.isfinite(float(value))
                or not 0 <= float(value) <= 100
            ):
                return None
            normalized_scores.append(float(value))
        if not isinstance(data["passed"], bool) or not isinstance(data["degraded"], bool):
            return None
        source = data["source"]
        if not isinstance(source, str) or source not in ANSWER_VERIFY_SOURCES:
            return None
        return {**data, "scores": normalized_scores}

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _post(
        self,
        path: str,
        payload: dict[str, Any],
        *,
        expected_keys: tuple[str, ...],
    ) -> dict[str, Any] | None:
        try:
            resp = await self._client.post(path, json=payload)
            resp.raise_for_status()
            data = resp.json()
        except (httpx.HTTPError, ValueError, ValidationError) as exc:
            logger.warning(
                "[ai:{code}] {path} call failed: {exc}",
                code=ErrorCode.AI_SERVICE_ERROR,
                path=path,
                exc=exc,
            )
            return None
        if not isinstance(data, dict) or not all(k in data for k in expected_keys):
            logger.warning(
                "[ai:{code}] {path} unexpected payload shape: keys={keys}",
                code=ErrorCode.AI_SERVICE_ERROR,
                path=path,
                keys=list(data.keys()) if isinstance(data, dict) else type(data).__name__,
            )
            return None
        return data
