from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic.alias_generators import to_camel

VALID_REVIEW_ACTIONS = {"APPROVE", "REJECT"}
VALID_REPORT_ACTIONS = {"VALID", "INVALID"}
VALID_ANNOUNCEMENT_STATUSES = {"DRAFT", "PUBLISHED", "OFFLINE"}
VALID_USER_STATUSES = {"ACTIVE", "DISABLED"}
VALID_BIZ_TYPES = {"LOST", "FOUND"}


class AdminPageQuery(BaseModel):
    page_no: int = Field(default=1, ge=1, alias="pageNo")
    page_size: int = Field(default=10, ge=1, le=50, alias="pageSize")
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class ReviewRequest(BaseModel):
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
    def validate_comment(self) -> "ReviewRequest":
        if self.action == "REJECT" and not self.comment:
            msg = "comment is required when action is REJECT"
            raise ValueError(msg)
        return self


class ReportHandleRequest(BaseModel):
    action: str
    result: str | None = Field(default=None, max_length=200)
    credit_delta: int | None = Field(default=None, alias="creditDelta")
    reason_code: str | None = Field(default=None, alias="reasonCode")
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        if v not in VALID_REPORT_ACTIONS:
            msg = f"action must be one of {VALID_REPORT_ACTIONS}"
            raise ValueError(msg)
        return v

    @model_validator(mode="after")
    def validate_result_and_penalty(self) -> "ReportHandleRequest":
        if self.action == "VALID" and not self.result:
            raise ValueError("result is required when action is VALID")
        if self.credit_delta is not None and self.credit_delta >= 0:
            raise ValueError("creditDelta must be negative")
        if self.action == "INVALID" and (
            self.credit_delta is not None or self.reason_code is not None
        ):
            raise ValueError("INVALID reports cannot include a penalty")
        return self


class AnnouncementCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    content: str = Field(..., min_length=1, max_length=5000)
    publish_now: bool = Field(default=True, alias="publishNow")
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class UserStatusRequest(BaseModel):
    status: str
    reason: str | None = Field(default=None, max_length=200)
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in VALID_USER_STATUSES:
            msg = f"status must be one of {VALID_USER_STATUSES}"
            raise ValueError(msg)
        return v

    @model_validator(mode="after")
    def validate_reason(self) -> "UserStatusRequest":
        if self.status == "DISABLED" and not self.reason:
            raise ValueError("reason is required when status is DISABLED")
        return self


class MatchIntervalRequest(BaseModel):
    interval_minutes: int = Field(..., ge=0, le=1440, alias="intervalMinutes")
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
