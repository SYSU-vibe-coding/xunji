from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic.alias_generators import to_camel

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
VALID_REVIEW_STATUSES = {
    "PENDING",
    "ANSWER_PASSED",
    "PROOF_PENDING",
    "APPROVED",
    "REJECTED",
    "APPEALING",
    "HANDED_OVER",
}
VALID_VERIFY_LEVELS = {"LEVEL_1", "LEVEL_2", "LEVEL_3", "FAST_TRACK"}
VALID_REVIEW_ACTIONS = {"APPROVE", "REJECT"}
VALID_HANDOVER_METHODS = {"MEETUP", "PICKUP_POINT"}
VALID_HANDOVER_ROLES = {"OWNER", "FINDER"}
VALID_MY_CLAIM_ROLES = {"CLAIMANT", "FINDER"}


def parse_datetime(value: str, field_name: str) -> datetime:
    try:
        return datetime.strptime(value, DATETIME_FORMAT)
    except ValueError as exc:
        msg = f"{field_name} must match yyyy-MM-dd HH:mm:ss"
        raise ValueError(msg) from exc


class ClaimAnswerInput(BaseModel):
    question_id: str = Field(..., alias="questionId")
    answer_text: str = Field(..., min_length=1, max_length=200, alias="answerText")
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class CreateClaimRequest(BaseModel):
    match_id: str | None = Field(default=None, alias="matchId")
    found_item_id: str = Field(..., alias="foundItemId")
    answers: list[ClaimAnswerInput] = Field(default_factory=list)
    proof_image_urls: list[str] = Field(default_factory=list, alias="proofImageUrls")
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    @field_validator("proof_image_urls")
    @classmethod
    def validate_proof_images(cls, v: list[str]) -> list[str]:
        if len(v) > 5:
            msg = "proofImageUrls 最多 5 张"
            raise ValueError(msg)
        return v


class CreateClaimResponse(BaseModel):
    id: str
    verify_level: str
    review_status: str
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class ClaimMyQuery(BaseModel):
    role: str = "CLAIMANT"
    review_status: str | None = Field(default=None, alias="reviewStatus")
    page_no: int = Field(default=1, ge=1, alias="pageNo")
    page_size: int = Field(default=10, ge=1, le=50, alias="pageSize")
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in VALID_MY_CLAIM_ROLES:
            msg = f"role must be one of {VALID_MY_CLAIM_ROLES}"
            raise ValueError(msg)
        return v


class ClaimMyListItem(BaseModel):
    id: str
    found_item_id: str
    item_name: str
    verify_level: str
    review_status: str
    updated_at: str
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class ClaimAnswerOutput(BaseModel):
    question_id: str
    question_text: str
    answer_text: str
    match_score: float
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class HandoverOutput(BaseModel):
    id: str
    method: str
    handover_location: str
    handover_time: str
    owner_confirmed: bool
    finder_confirmed: bool
    completed_at: str | None = None
    created_at: str
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class ClaimDetailResponse(BaseModel):
    id: str
    match_id: str | None = None
    found_item_id: str
    claimant_id: str
    verify_level: str
    review_status: str
    reject_reason: str | None = None
    answers: list[ClaimAnswerOutput] = Field(default_factory=list)
    proof_image_urls: list[str] = Field(default_factory=list)
    proof_text: str | None = None
    handover: HandoverOutput | None = None
    claimed_at: str
    updated_at: str
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class ClaimReviewRequest(BaseModel):
    action: str
    comment: str | None = Field(default=None, max_length=200)
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        if v not in VALID_REVIEW_ACTIONS:
            msg = f"action must be one of {VALID_REVIEW_ACTIONS}"
            raise ValueError(msg)
        return v

    @model_validator(mode="after")
    def validate_comment(self) -> "ClaimReviewRequest":
        if self.action == "REJECT" and not self.comment:
            msg = "comment is required when action is REJECT"
            raise ValueError(msg)
        return self


class ClaimProofsRequest(BaseModel):
    proof_image_urls: list[str] = Field(..., min_length=1, max_length=5, alias="proofImageUrls")
    proof_text: str | None = Field(default=None, max_length=500, alias="proofText")
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class ClaimAppealRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=500)
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class CreateHandoverRequest(BaseModel):
    method: str
    handover_location: str = Field(..., min_length=1, max_length=100, alias="handoverLocation")
    handover_time: str = Field(..., alias="handoverTime")
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    @field_validator("method")
    @classmethod
    def validate_method(cls, v: str) -> str:
        if v not in VALID_HANDOVER_METHODS:
            msg = f"method must be one of {VALID_HANDOVER_METHODS}"
            raise ValueError(msg)
        return v

    @field_validator("handover_time")
    @classmethod
    def validate_time(cls, v: str) -> str:
        parse_datetime(v, "handoverTime")
        return v


class CreateHandoverResponse(BaseModel):
    handover_id: str
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class ConfirmHandoverRequest(BaseModel):
    role: str
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in VALID_HANDOVER_ROLES:
            msg = f"role must be one of {VALID_HANDOVER_ROLES}"
            raise ValueError(msg)
        return v
