from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic.alias_generators import to_camel

VALID_MATCH_BIZ_TYPES = {"LOST", "FOUND"}
VALID_MATCH_STATUSES = {"NEW", "READ", "CLAIMED", "EXPIRED"}


def normalize_biz_type(value: str | None) -> str | None:
    if not value:  # empty string or None
        return None
    normalized = value.upper()
    if normalized not in VALID_MATCH_BIZ_TYPES:
        msg = "bizType must be LOST or FOUND"
        raise ValueError(msg)
    return normalized


class MatchListQuery(BaseModel):
    biz_type: str | None = Field(default=None, alias="bizType")
    biz_id: str | None = Field(default=None, alias="bizId")
    page_no: int = Field(default=1, ge=1, alias="pageNo")
    page_size: int = Field(default=10, ge=1, le=50, alias="pageSize")
    min_score: float = Field(default=70, ge=0, le=100, alias="minScore")
    status: str | None = None
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    @field_validator("biz_type")
    @classmethod
    def validate_biz_type(cls, value: str | None) -> str | None:
        return normalize_biz_type(value)

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.upper()
        if normalized not in VALID_MATCH_STATUSES:
            msg = f"status must be one of {VALID_MATCH_STATUSES}"
            raise ValueError(msg)
        return normalized

    @model_validator(mode="after")
    def validate_biz_pair(self) -> "MatchListQuery":
        if (self.biz_type is None) != (self.biz_id is None):
            raise ValueError("bizType and bizId must be provided together")
        return self


class MatchRecalculateRequest(BaseModel):
    biz_type: str = Field(..., alias="bizType")
    biz_id: str = Field(..., alias="bizId")
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    @field_validator("biz_type")
    @classmethod
    def validate_biz_type(cls, value: str) -> str:
        result = normalize_biz_type(value)
        if result is None:
            msg = "bizType must be LOST or FOUND"
            raise ValueError(msg)
        return result


class MatchCounterpartSummary(BaseModel):
    id: str
    item_name: str
    category: str
    cover_image_url: str | None = None
    location: str
    time: str
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class MatchListItem(BaseModel):
    match_id: str
    lost_item_id: str
    found_item_id: str
    image_score: float
    text_score: float
    location_score: float
    time_score: float
    total_score: float
    image_available: bool
    degraded: bool
    score_source: Literal[
        "RULE_BASED",
        "TEXT_MODEL_RULES",
        "MULTIMODAL_MODEL",
        "LEGACY_RENORMALIZED",
    ]
    match_status: str
    counterpart: MatchCounterpartSummary
    created_at: str
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class MatchDetailResponse(MatchListItem):
    lost_item: dict[str, Any]
    found_item: dict[str, Any]
    can_claim: bool
    claim_id: str | None = None
    claim_status: str | None = None


class MatchRecalculateResponse(BaseModel):
    matched_count: int
    status: Literal["COMPLETED"] = "COMPLETED"
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
