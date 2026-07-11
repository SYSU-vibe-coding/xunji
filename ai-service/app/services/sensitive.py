"""Sensitive item detection. Tries DashScope VL, falls back to keyword baseline."""

from __future__ import annotations

from loguru import logger

from app.clients.dashscope import DashScopeClient
from app.schemas import DetectSensitiveRequest, DetectSensitiveResponse
from app.services import _baseline

SENSITIVE_PROMPT = (
    "请判断这张图是否包含可识别的实体证件 (如身份证/学生证/校园卡/银行卡).\n"
    "只回答以下五个英文代号之一: ID_CARD, CAMPUS_CARD, BANK_CARD, OTHER, NONE.\n"
    "其中 NONE 表示不含任何证件; OTHER 表示含证件但不属于前三类. 不要解释."
)
VALID = {"ID_CARD", "CAMPUS_CARD", "BANK_CARD", "OTHER"}


async def detect_sensitive(
    req: DetectSensitiveRequest, client: DashScopeClient | None
) -> DetectSensitiveResponse:
    if client is None or not client.enabled:
        return _baseline.detect_sensitive(req)

    try:
        reply = await client.vl_understand(req.image_url, SENSITIVE_PROMPT)
    except Exception:
        logger.exception("[ai:50002] sensitive VL failed unexpectedly")
        return _baseline.detect_sensitive(req)
    if not reply:
        return _baseline.detect_sensitive(req)

    category = _parse_sensitive(reply)
    if category is None:
        # Treat unparseable response as "not confident" → fall back so we
        # don't accidentally tag everything as non-sensitive.
        logger.warning("[ai:50002] sensitive VL returned unparseable text: {!r}", reply[:80])
        return _baseline.detect_sensitive(req)

    if category == "NONE":
        return DetectSensitiveResponse(
            is_sensitive=False,
            sensitive_type=None,
            masked_image_url=None,
            recognized_fields=None,
            degraded=False,
            needs_review=False,
        )
    return DetectSensitiveResponse(
        is_sensitive=True,
        sensitive_type=category,
        # Detection does not create an actual redacted object yet. Never
        # present the source URL plus a query flag as a masked copy.
        masked_image_url=None,
        recognized_fields=None,
        degraded=True,
        needs_review=True,
    )


def _parse_sensitive(reply: str) -> str | None:
    upper = reply.upper()
    if "NONE" in upper:
        return "NONE"
    for label in VALID:
        if label in upper:
            return label
    return None
