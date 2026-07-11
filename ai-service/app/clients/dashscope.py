"""Thin async client for LLM providers.

Supports two API styles:
- **DashScope-native** (Alibaba BaiLian): uses ``/services/embeddings/...``
  and ``/services/aigc/multimodal-generation/generation``.
- **OpenAI-compatible** (SiliconFlow, OpenAI, etc.): uses ``/embeddings``
  and ``/chat/completions``.

The style is auto-detected from the base URL. When ``LLM_MODEL`` is set,
text similarity scoring uses a chat-completion prompt (asks the model to
rate similarity 0-100). When only ``DASHSCOPE_TEXT_EMBEDDING_MODEL`` /
``TEXT_EMBEDDING_MODEL`` is set, embeddings + cosine similarity are used.

All public methods return ``None`` on any kind of failure (network error,
non-2xx, malformed response). Callers MUST treat ``None`` as "fall back to
the keyword baseline" — no exception is propagated.
"""

from __future__ import annotations

import re
from typing import Any

import httpx
from loguru import logger

from app.clients.image_fetcher import (
    ImageDownloadError,
    ImageFetcher,
    ImageHostResolver,
)
from app.core.config import settings


class DashScopeClient:
    """Async LLM wrapper. One per process; share via FastAPI lifespan."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
        image_transport: httpx.AsyncBaseTransport | None = None,
        image_resolver: ImageHostResolver | None = None,
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
        self._image_fetcher = ImageFetcher(
            transport=image_transport,
            resolver=image_resolver,
        )

    async def aclose(self) -> None:
        await self._client.aclose()
        await self._image_fetcher.aclose()

    @property
    def enabled(self) -> bool:
        return bool(self._api_key)

    @property
    def _openai_mode(self) -> bool:
        return "dashscope.aliyuncs.com" not in self._base_url

    # ------------------------------------------------------------------
    # Text similarity (high-level convenience for match service)
    # ------------------------------------------------------------------

    async def text_similarity_score(
        self,
        lost_text: str,
        found_text: str,
    ) -> float | None:
        """Rate text similarity 0-100 using the configured LLM or embeddings.

        Returns ``None`` on any failure so the caller can fall back to the
        keyword baseline.
        """
        if not self.enabled or not lost_text or not found_text:
            return None

        if settings.LLM_MODEL:
            return await self._chat_similarity(lost_text, found_text)

        embedding_model = settings.TEXT_EMBEDDING_MODEL or settings.DASHSCOPE_TEXT_EMBEDDING_MODEL
        if embedding_model:
            vectors = await self.text_embedding([lost_text, found_text])
            if vectors is None or len(vectors) != 2:
                return None
            return _cosine_pct(vectors[0], vectors[1])

        return None

    # ------------------------------------------------------------------
    # Chat completion (OpenAI-compatible)
    # ------------------------------------------------------------------

    async def chat_completion(self, system_prompt: str, user_prompt: str) -> str | None:
        """Call ``/chat/completions`` and return the assistant message text."""
        if not self.enabled:
            return None
        model = settings.LLM_MODEL
        if not model:
            return None
        payload: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.0,
            "max_tokens": 64,
        }
        path = (
            "/chat/completions"
            if self._openai_mode
            else ("/services/aigc/text-generation/generation")
        )
        try:
            resp = await self._client.post(path, json=payload)
            resp.raise_for_status()
            data = resp.json()
            if self._openai_mode:
                choices = data.get("choices", [])
                if not choices:
                    return None
                content = choices[0].get("message", {}).get("content")
                return content.strip() if isinstance(content, str) and content.strip() else None
            # DashScope text-generation format
            output = data.get("output", {})
            text = output.get("text")
            return text.strip() if isinstance(text, str) and text.strip() else None
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            logger.warning("[ai:50002] chat_completion failed: {}", exc)
            return None

    async def _chat_similarity(
        self,
        lost_text: str,
        found_text: str,
    ) -> float | None:
        """Ask the LLM to rate how likely these two items are the same, 0-100."""
        system = (
            "你是一个失物招领匹配助手。给定一条失物信息和一条招领信息，"
            "判断它们是否指向同一件物品，并给出一个 0 到 100 的相似度分数。"
            "只回复一个数字，不要有任何其他文字。"
        )
        user = (
            f"失物名称与描述: {lost_text}\n招领名称与描述: {found_text}\n请给出相似度分数 (0-100):"
        )
        raw = await self.chat_completion(system, user)
        if raw is None:
            return None
        match = re.search(r"\d+(?:\.\d+)?", raw)
        if not match:
            logger.warning("[ai:50002] chat_similarity unparseable reply: {}", raw[:80])
            return None
        try:
            score = float(match.group())
        except ValueError:
            return None
        return max(0.0, min(100.0, score))

    # ------------------------------------------------------------------
    # Text embedding
    # ------------------------------------------------------------------

    async def text_embedding(self, texts: list[str]) -> list[list[float]] | None:
        """Return one embedding vector per input text, or ``None`` on failure."""
        if not self.enabled or not texts:
            return None
        model = settings.TEXT_EMBEDDING_MODEL or settings.DASHSCOPE_TEXT_EMBEDDING_MODEL
        if not model:
            return None

        if self._openai_mode:
            return await self._embedding_openai(model, texts)
        return await self._embedding_dashscope(model, texts)

    async def _embedding_openai(self, model: str, texts: list[str]) -> list[list[float]] | None:
        payload = {"model": model, "input": texts}
        try:
            resp = await self._client.post("/embeddings", json=payload)
            resp.raise_for_status()
            data = resp.json()
            items = data.get("data", [])
            vectors = [item.get("embedding") for item in items if item.get("embedding")]
            if len(vectors) != len(texts):
                logger.warning(
                    "[ai:50002] embedding_openai returned {} for {} inputs",
                    len(vectors),
                    len(texts),
                )
                return None
            return vectors
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            logger.warning("[ai:50002] embedding_openai failed: {}", exc)
            return None

    async def _embedding_dashscope(self, model: str, texts: list[str]) -> list[list[float]] | None:
        payload = {
            "model": model,
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
        vl_model = settings.DASHSCOPE_VL_MODEL
        if not vl_model:
            return None
        try:
            image_source = await self._image_fetcher.fetch_data_uri(image_url)
        except ImageDownloadError as exc:
            logger.warning("[ai:50002] VL image download rejected: {}", str(exc))
            return None

        if self._openai_mode:
            return await self._vl_openai(vl_model, image_source, prompt)
        return await self._vl_dashscope(vl_model, image_source, prompt)

    async def _vl_openai(self, model: str, image_url: str, prompt: str) -> str | None:
        payload: dict[str, Any] = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": image_url}},
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
            "max_tokens": 512,
        }
        try:
            resp = await self._client.post("/chat/completions", json=payload)
            resp.raise_for_status()
            data = resp.json()
            choices = data.get("choices", [])
            if not choices:
                return None
            content = choices[0].get("message", {}).get("content")
            return content.strip() if isinstance(content, str) and content.strip() else None
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            logger.warning("[ai:50002] vl_openai failed: {}", exc)
            return None

    async def _vl_dashscope(self, model: str, image_url: str, prompt: str) -> str | None:
        payload: dict[str, Any] = {
            "model": model,
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


def _cosine_pct(a: list[float], b: list[float]) -> float:
    import math

    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return max(0.0, min(100.0, dot / (norm_a * norm_b) * 100.0))
