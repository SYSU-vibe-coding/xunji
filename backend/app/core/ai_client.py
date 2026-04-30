"""HTTP client for the standalone AI service.

Wraps the three internal endpoints documented in ``docs/api/ai-service.md``
and applies the 3-second timeout budget the document promises. Every method
returns ``None`` on failure (timeout, non-2xx, malformed payload). Callers
MUST treat ``None`` as "fall back" — no exception is propagated, so a
broken AI service never breaks a main-backend transaction.
"""

from __future__ import annotations

from typing import Any

import httpx
from loguru import logger
from pydantic import ValidationError

from app.common.errors import ErrorCode
from app.core.config import settings


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
        return await self._post(
            "/internal/ai/calculate-match",
            {"lostItem": lost, "foundItem": found},
            expected_keys=("imageScore", "textScore", "locationScore", "timeScore", "totalScore"),
        )

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
        return await self._post(
            "/internal/ai/classify-item",
            payload,
            expected_keys=("category", "tags", "confidence"),
        )

    async def detect_sensitive(self, image_url: str) -> dict[str, Any] | None:
        if not image_url:
            return None
        return await self._post(
            "/internal/ai/detect-sensitive",
            {"imageUrl": image_url},
            expected_keys=("isSensitive",),
        )

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
