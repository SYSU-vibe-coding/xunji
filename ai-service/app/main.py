"""Xunji AI service entrypoint.

Endpoints:
- ``GET  /health``                       - liveness probe
- ``POST /internal/ai/classify-item``    - VL classification, baseline fallback
- ``POST /internal/ai/detect-sensitive`` - VL sensitive detection, baseline fallback
- ``POST /internal/ai/calculate-match``  - embedding similarity, baseline fallback

The ``DashScopeClient`` is owned by the FastAPI application via the lifespan
context, so each request reuses the underlying ``httpx.AsyncClient`` pool.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from app.clients.dashscope import DashScopeClient
from app.core.config import settings
from app.schemas import (
    CalculateMatchRequest,
    CalculateMatchResponse,
    ClassifyItemRequest,
    ClassifyItemResponse,
    DetectSensitiveRequest,
    DetectSensitiveResponse,
)
from app.services import classify, match, sensitive


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    client = DashScopeClient()
    app.state.dashscope = client
    try:
        yield
    finally:
        await client.aclose()


def _client(request: Request) -> DashScopeClient | None:
    return getattr(request.app.state, "dashscope", None)


def create_app() -> FastAPI:
    app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION, lifespan=lifespan)

    @app.get("/health")
    async def health() -> dict[str, str | bool]:
        return {"status": "ok", "dashscope": settings.use_dashscope}

    @app.post("/internal/ai/classify-item")
    async def classify_item_endpoint(
        req: ClassifyItemRequest, request: Request
    ) -> ClassifyItemResponse:
        return await classify.classify_item(req, _client(request))

    @app.post("/internal/ai/detect-sensitive")
    async def detect_sensitive_endpoint(
        req: DetectSensitiveRequest, request: Request
    ) -> DetectSensitiveResponse:
        return await sensitive.detect_sensitive(req, _client(request))

    @app.post("/internal/ai/calculate-match")
    async def calculate_match_endpoint(
        req: CalculateMatchRequest, request: Request
    ) -> CalculateMatchResponse:
        return await match.calculate_match(req, _client(request))

    return app


app = create_app()
// lin-hongkuan: AI服务集成
