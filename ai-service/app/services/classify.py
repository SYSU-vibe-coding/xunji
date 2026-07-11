"""Item classification service. Tries DashScope VL, falls back to baseline."""

from __future__ import annotations

from loguru import logger

from app.clients.dashscope import DashScopeClient
from app.schemas import ClassifyItemRequest, ClassifyItemResponse
from app.services import _baseline

CLASSIFY_PROMPT = (
    "请将图片中的物品归类为以下五类之一, 只返回类别英文代号本身, 不要其它文字:\n"
    "CERT (证件/卡片), ELECTRONIC (电子产品), BOOK (书本), "
    "DAILY_USE (日常用品), OTHER (其它)"
)
VALID = {"CERT", "ELECTRONIC", "BOOK", "DAILY_USE", "OTHER"}


async def classify_item(
    req: ClassifyItemRequest, client: DashScopeClient | None
) -> ClassifyItemResponse:
    if client is None or not client.enabled or not req.image_urls:
        return _baseline.classify_item(req)

    try:
        reply = await client.vl_understand(req.image_urls[0], CLASSIFY_PROMPT)
    except Exception:
        logger.exception("[ai:50002] classify VL failed unexpectedly")
        return _baseline.classify_item(req)
    if not reply:
        return _baseline.classify_item(req)

    category = _parse_category(reply)
    if category is None:
        logger.warning("[ai:50002] classify VL returned unparseable text: {!r}", reply[:80])
        return _baseline.classify_item(req)

    # Use the baseline keyword pass to enrich tags; confidence comes from VL hit.
    baseline = _baseline.classify_item(req)
    return ClassifyItemResponse(
        category=category,
        tags=baseline.tags,
        confidence=85.0,
        degraded=False,
        source="VISION_MODEL",
    )


def _parse_category(reply: str) -> str | None:
    upper = reply.upper()
    for label in VALID:
        if label in upper:
            return label
    return None
