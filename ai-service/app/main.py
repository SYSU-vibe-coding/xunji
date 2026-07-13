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

import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Request, status

from app.clients.dashscope import DashScopeClient
from app.core.config import Settings, settings
from app.schemas import (
    CalculateMatchRequest,
    CalculateMatchResponse,
    ClassifyItemRequest,
    ClassifyItemResponse,
    DetectSensitiveRequest,
    DetectSensitiveResponse,
    VerifyClaimAnswersRequest,
    VerifyClaimAnswersResponse,
)
from app.services import answer, classify, match, sensitive


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


SERVICE_TOKEN_HEADER = "X-Service-Token"


def create_app(app_settings: Settings | None = None) -> FastAPI:
    runtime_settings = app_settings or settings
    app = FastAPI(
        title=runtime_settings.APP_NAME,
        version=runtime_settings.APP_VERSION,
        lifespan=lifespan,
    )

    async def require_service_token(
        supplied_token: Annotated[str | None, Header(alias=SERVICE_TOKEN_HEADER)] = None,
    ) -> None:
        expected_token = runtime_settings.AI_SERVICE_TOKEN
        if runtime_settings.AI_LOCAL_DEV_MODE and not expected_token:
            return
        token_matches = supplied_token is not None and secrets.compare_digest(
            supplied_token.encode(), expected_token.encode()
        )
        if not token_matches:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid service token",
            )

    internal = APIRouter(
        prefix="/internal/ai",
        dependencies=[Depends(require_service_token)],
    )

    @app.get("/health")
    async def health() -> dict[str, str | bool]:
        return {"status": "ok", "dashscope": runtime_settings.use_dashscope}

    @internal.post("/classify-item")
    async def classify_item_endpoint(
        req: ClassifyItemRequest, request: Request
    ) -> ClassifyItemResponse:
        return await classify.classify_item(req, _client(request))

    @internal.post("/detect-sensitive")
    async def detect_sensitive_endpoint(
        req: DetectSensitiveRequest, request: Request
    ) -> DetectSensitiveResponse:
        return await sensitive.detect_sensitive(req, _client(request))

    @internal.post("/calculate-match")
    async def calculate_match_endpoint(
        req: CalculateMatchRequest, request: Request
    ) -> CalculateMatchResponse:
        return await match.calculate_match(req, _client(request))

    @internal.post("/verify-claim-answers")
    async def verify_claim_answers_endpoint(
        req: VerifyClaimAnswersRequest, request: Request
    ) -> VerifyClaimAnswersResponse:
        return await answer.verify_claim_answers(req, _client(request))

    app.include_router(internal)
    return app


app = create_app()
