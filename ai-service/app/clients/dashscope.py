"""Thin async client for Alibaba Cloud DashScope (BaiLian) APIs.

Wraps two surfaces we use:
- text-embedding (used for similarity scoring)
- multimodal generation / VL (used for sensitive detection and classification)

All public methods return ``None`` on any kind of failure (network error,
non-2xx, malformed response). Callers MUST treat ``None`` as "fall back to
the keyword baseline" — no exception is propagated.
"""

from __future__ import annotations

from typing import Any

import httpx
from loguru import logger

from app.core.config import settings


class DashScopeClient:
    """Async DashScope wrapper. One per process; share via FastAPI lifespan."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._api_key = api_key if api_key is not None else settings.DASHSCOPE_API_KEY
        self._base_url = (base_url or settings.DASHSCOPE_BASE_URL).rstrip("/")
        self._timeout = timeout if timeout is not None else settings.DASHSCOPE_TIMEOUT
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=self._timeout,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            transport=transport,
            # Don't pick up host-level proxy env vars (e.g. socks://) which
            # httpx may not understand. Outbound traffic, if any, goes
            # through the explicit base_url.
            trust_env=False,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    @property
    def enabled(self) -> bool:
        return bool(self._api_key)

    # ------------------------------------------------------------------
    # Text embedding
    # ------------------------------------------------------------------

    async def text_embedding(self, texts: list[str]) -> list[list[float]] | None:
        """Return one embedding vector per input text, or ``None`` on failure."""
        if not self.enabled or not texts:
            return None
        payload = {
            "model": settings.DASHSCOPE_TEXT_EMBEDDING_MODEL,
            "input": {"texts": texts},
            "parameters": {"text_type": "query"},
        }
        try:
            resp = await self._client.post(
                "/services/embeddings/text-embedding/text-embedding", json=payload
            )
            resp.raise_for_status()
            data = resp.json()
            embeddings = data.get("output", {}).get("embeddings", [])
            vectors = [item.get("embedding") for item in embeddings if item.get("embedding")]
            if len(vectors) != len(texts):
                logger.warning(
                    "[ai:50002] text_embedding returned {} vectors for {} inputs",
                    len(vectors),
                    len(texts),
                )
                return None
            return vectors
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            logger.warning("[ai:50002] text_embedding failed: {}", exc)
            return None

    # ------------------------------------------------------------------
    # Vision-language (multimodal) understanding
    # ------------------------------------------------------------------

    async def vl_understand(self, image_url: str, prompt: str) -> str | None:
        """Ask a VL model about an image, return the raw text reply or ``None``."""
        if not self.enabled or not image_url or not prompt:
            return None
        payload: dict[str, Any] = {
            "model": settings.DASHSCOPE_VL_MODEL,
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"image": image_url},
                            {"text": prompt},
                        ],
                    }
                ]
            },
            "parameters": {"result_format": "message"},
        }
        try:
            resp = await self._client.post(
                "/services/aigc/multimodal-generation/generation", json=payload
            )
            resp.raise_for_status()
            data = resp.json()
            choices = data.get("output", {}).get("choices", [])
            if not choices:
                logger.warning("[ai:50002] vl_understand returned no choices")
                return None
            content = choices[0].get("message", {}).get("content")
            # DashScope returns content as either str or list of {text: ...}
            if isinstance(content, str):
                return content.strip() or None
            if isinstance(content, list):
                parts = [
                    item.get("text", "")
                    for item in content
                    if isinstance(item, dict) and item.get("text")
                ]
                joined = " ".join(parts).strip()
                return joined or None
            logger.warning("[ai:50002] vl_understand unexpected content type: {}", type(content))
            return None
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            logger.warning("[ai:50002] vl_understand failed: {}", exc)
            return None
