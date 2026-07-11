from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel

VALID_NOTICE_TYPES = {
    "MATCH_RECOMMEND",
    "CLAIM_REQUEST",
    "CLAIM_REVIEW",
    "HANDOVER_REMINDER",
    "CREDIT_CHANGED",
    "SYSTEM_ANNOUNCEMENT",
}
VALID_NOTIFICATION_PRIORITIES = {"NORMAL", "HIGH"}


def _validate_optional_enum(value: str | None, allowed: set[str], field_name: str) -> str | None:
    if value is not None and value not in allowed:
        msg = f"{field_name} must be one of {allowed}"
        raise ValueError(msg)
    return value


class NotificationQuery(BaseModel):
    page_no: int = Field(default=1, ge=1, alias="pageNo")
    page_size: int = Field(default=10, ge=1, le=50, alias="pageSize")
    is_read: bool | None = Field(default=None, alias="isRead")
    notice_type: str | None = Field(default=None, alias="noticeType")
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    @field_validator("notice_type")
    @classmethod
    def validate_notice_type(cls, v: str | None) -> str | None:
        return _validate_optional_enum(v, VALID_NOTICE_TYPES, "noticeType")


class NotificationListItem(BaseModel):
    id: str
    notice_type: str
    title: str
    content: str | None = None
    is_read: bool
    related_type: str | None = None
    related_id: str | None = None
    priority: str
    created_at: str
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class ReadAllRequest(BaseModel):
    notice_type: str | None = Field(default=None, alias="noticeType")
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    @field_validator("notice_type")
    @classmethod
    def validate_notice_type(cls, v: str | None) -> str | None:
        return _validate_optional_enum(v, VALID_NOTICE_TYPES, "noticeType")


class UnreadCountResponse(BaseModel):
    total: int
    by_type: dict[str, int]
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class AnnouncementListItem(BaseModel):
    id: str
    title: str
    published_at: str
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class AnnouncementDetail(BaseModel):
    id: str
    title: str
    content: str
    published_at: str
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
