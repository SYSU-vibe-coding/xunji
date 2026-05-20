import re
from collections.abc import Iterable

from app.schemas import (
    CalculateMatchRequest,
    CalculateMatchResponse,
    ClassifyItemRequest,
    ClassifyItemResponse,
    DetectSensitiveRequest,
    DetectSensitiveResponse,
)

CATEGORY_KEYWORDS: dict[str, set[str]] = {
    "CERT": {"证", "卡", "身份证", "学生证", "校园卡", "一卡通", "id", "card"},
    "ELECTRONIC": {"手机", "电脑", "耳机", "平板", "相机", "iphone", "macbook"},
    "BOOK": {"书", "教材", "笔记本", "作业本", "book"},
    "DAILY_USE": {"伞", "杯", "钥匙", "钱包", "衣服", "umbrella", "cup", "key", "wallet"},
}
SENSITIVE_KEYWORDS = {"身份证", "学生证", "校园卡", "一卡通", "银行卡", "id", "card"}


def classify_item(req: ClassifyItemRequest) -> ClassifyItemResponse:
    text = _combined_text([req.item_name, req.description, *req.image_urls])
    best_category = "OTHER"
    best_hits = 0
    tags: list[str] = []
    for category, keywords in CATEGORY_KEYWORDS.items():
        hits = [keyword for keyword in keywords if keyword.lower() in text]
        if len(hits) > best_hits:
            best_category = category
            best_hits = len(hits)
            tags = hits[:10]
    confidence = min(100.0, 50.0 + best_hits * 20.0) if best_hits else 50.0
    return ClassifyItemResponse(category=best_category, tags=tags, confidence=confidence)


def detect_sensitive(req: DetectSensitiveRequest) -> DetectSensitiveResponse:
    text = req.image_url.lower()
    is_sensitive = any(keyword.lower() in text for keyword in SENSITIVE_KEYWORDS)
    sensitive_type = None
    if is_sensitive:
        if "bank" in text or "银行卡" in text:
            sensitive_type = "BANK_CARD"
        elif "id" in text or "身份证" in text:
            sensitive_type = "ID_CARD"
        elif "校园卡" in text or "学生证" in text or "card" in text:
            sensitive_type = "CAMPUS_CARD"
        else:
            sensitive_type = "OTHER"
    return DetectSensitiveResponse(
        is_sensitive=is_sensitive,
        sensitive_type=sensitive_type,
        masked_image_url=f"{req.image_url}?masked=1" if is_sensitive else None,
        recognized_fields=None,
    )


def calculate_match(req: CalculateMatchRequest) -> CalculateMatchResponse:
    image_score = 60.0 if req.lost_item.image_urls and req.found_item.image_urls else 0.0
    text_score = _keyword_overlap(
        [req.lost_item.name, req.lost_item.description],
        [req.found_item.name, req.found_item.description],
    )
    location_score = _location_score(req.lost_item.location, req.found_item.location)
    time_score = 50.0 if req.lost_item.time and req.found_item.time else 0.0
    total_score = image_score * 0.4 + text_score * 0.3 + location_score * 0.2 + time_score * 0.1
    return CalculateMatchResponse(
        image_score=round(image_score, 2),
        text_score=round(text_score, 2),
        location_score=round(location_score, 2),
        time_score=round(time_score, 2),
        total_score=round(total_score, 2),
    )


def _combined_text(values: Iterable[str | None]) -> str:
    return " ".join(value for value in values if value).lower()


def _tokens(values: Iterable[str | None]) -> set[str]:
    text = _combined_text(values)
    return {token for token in re.split(r"\W+", text) if token}


def _keyword_overlap(left: Iterable[str | None], right: Iterable[str | None]) -> float:
    left_tokens = _tokens(left)
    right_tokens = _tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens) * 100


def _location_score(left: str | None, right: str | None) -> float:
    if not left or not right:
        return 0.0
    if left == right:
        return 100.0
    return 60.0 if left[:2] == right[:2] else 0.0
