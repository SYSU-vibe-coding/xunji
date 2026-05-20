from fastapi import FastAPI

from app.schemas import (
    CalculateMatchRequest,
    CalculateMatchResponse,
    ClassifyItemRequest,
    ClassifyItemResponse,
    DetectSensitiveRequest,
    DetectSensitiveResponse,
)
from app.service import calculate_match, classify_item, detect_sensitive


def create_app() -> FastAPI:
    app = FastAPI(title="Xunji AI Service", version="0.1.0")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/internal/ai/classify-item")
    async def classify_item_endpoint(req: ClassifyItemRequest) -> ClassifyItemResponse:
        return classify_item(req)

    @app.post("/internal/ai/detect-sensitive")
    async def detect_sensitive_endpoint(req: DetectSensitiveRequest) -> DetectSensitiveResponse:
        return detect_sensitive(req)

    @app.post("/internal/ai/calculate-match")
    async def calculate_match_endpoint(req: CalculateMatchRequest) -> CalculateMatchResponse:
        return calculate_match(req)

    return app


app = create_app()
