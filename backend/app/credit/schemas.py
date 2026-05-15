from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel

VALID_CREDIT_REASON_CODES = {
    "HANDOVER_SUCCESS",
    "FOUND_ITEM_PUBLISHED",
    "PEER_GOOD_REVIEW",
    "CERT_APPROVED",
    "CLAIM_REJECTED_NO_APPEAL",
    "FRAUD_CLAIM_CONFIRMED",
    "FAKE_PUBLISH_CONFIRMED",
    "CLAIM_TIMEOUT_NO_REPLY",
}


class CreditLogItem(BaseModel):
    id: str
    user_id: str
    delta_score: int
    reason_code: str
    reason_text: str | None = None
    biz_type: str
    biz_id: str
    created_at: str
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class CreditLogQuery(BaseModel):
    page_no: int = Field(default=1, ge=1, alias="pageNo")
    page_size: int = Field(default=10, ge=1, le=50, alias="pageSize")
    reason_code: str | None = Field(default=None, alias="reasonCode")
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    @field_validator("reason_code")
    @classmethod
    def validate_reason_code(cls, v: str | None) -> str | None:
        if v is not None and v not in VALID_CREDIT_REASON_CODES:
            msg = f"reasonCode must be one of {VALID_CREDIT_REASON_CODES}"
            raise ValueError(msg)
        return v
