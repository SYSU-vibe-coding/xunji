from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator, model_validator
from pydantic.alias_generators import to_camel

# ---- Enums for validation ----
VALID_ITEM_CATEGORIES = {"CERT", "ELECTRONIC", "DAILY_USE", "BOOK", "OTHER"}
VALID_LOST_STATUSES = {"SEARCHING", "FOUND", "CLOSED"}
VALID_FOUND_STATUSES = {"PENDING", "CLAIMING", "RETURNED", "CLOSED"}
VALID_REVIEW_STATUSES = {"PENDING", "APPROVED", "REJECTED"}
VALID_CUSTODY_TYPES = {"SELF", "SECURITY", "OFFICE"}
VALID_CONTACT_PREFERENCES = {"IN_APP", "PHONE"}
VALID_BIZ_TYPES = {"LOST", "FOUND", "CLAIM_PROOF", "CERT"}
VALID_SORT_OPTIONS = {"CREATED_DESC", "CREATED_ASC"}
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def _parse_datetime(value: str, field_name: str) -> datetime:
    try:
        return datetime.strptime(value, DATETIME_FORMAT)
    except ValueError as exc:
        msg = f"{field_name} must match yyyy-MM-dd HH:mm:ss"
        raise ValueError(msg) from exc


def _validate_optional_enum(value: str | None, allowed: set[str], field_name: str) -> str | None:
    if value is not None and value not in allowed:
        msg = f"{field_name} must be one of {allowed}"
        raise ValueError(msg)
    return value


# ---- Lost item ----


class CreateLostItemRequest(BaseModel):
    item_name: str = Field(..., min_length=1, max_length=100)
    category: str
    description: str | None = Field(None, max_length=500)
    lost_time_start: str  # yyyy-MM-dd HH:mm:ss
    lost_time_end: str
    lost_location: str = Field(..., min_length=1, max_length=100)
    subscribe_match: bool = False
    image_urls: list[str] = Field(default_factory=list)
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        if v not in VALID_ITEM_CATEGORIES:
            msg = f"category must be one of {VALID_ITEM_CATEGORIES}"
            raise ValueError(msg)
        return v

    @field_validator("lost_time_start", "lost_time_end")
    @classmethod
    def validate_lost_time_format(cls, v: str, info: ValidationInfo) -> str:
        _parse_datetime(v, info.field_name or "datetime")
        return v

    @model_validator(mode="after")
    def validate_lost_time_range(self) -> "CreateLostItemRequest":
        start = _parse_datetime(self.lost_time_start, "lostTimeStart")
        end = _parse_datetime(self.lost_time_end, "lostTimeEnd")
        if end < start:
            msg = "lostTimeEnd must be greater than or equal to lostTimeStart"
            raise ValueError(msg)
        return self

    @field_validator("image_urls")
    @classmethod
    def validate_image_count(cls, v: list[str]) -> list[str]:
        if len(v) > 5:
            msg = "最多上传5张图片"
            raise ValueError(msg)
        return v


class CreateLostItemResponse(BaseModel):
    id: str
    status: str
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class UpdateLostItemRequest(BaseModel):
    item_name: str = Field(..., min_length=1, max_length=100)
    category: str
    description: str | None = Field(None, max_length=500)
    lost_time_start: str
    lost_time_end: str
    lost_location: str = Field(..., min_length=1, max_length=100)
    subscribe_match: bool = False
    image_urls: list[str] = Field(default_factory=list)
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        if v not in VALID_ITEM_CATEGORIES:
            msg = f"category must be one of {VALID_ITEM_CATEGORIES}"
            raise ValueError(msg)
        return v

    @field_validator("lost_time_start", "lost_time_end")
    @classmethod
    def validate_lost_time_format(cls, v: str, info: ValidationInfo) -> str:
        _parse_datetime(v, info.field_name or "datetime")
        return v

    @model_validator(mode="after")
    def validate_lost_time_range(self) -> "UpdateLostItemRequest":
        start = _parse_datetime(self.lost_time_start, "lostTimeStart")
        end = _parse_datetime(self.lost_time_end, "lostTimeEnd")
        if end < start:
            msg = "lostTimeEnd must be greater than or equal to lostTimeStart"
            raise ValueError(msg)
        return self

    @field_validator("image_urls")
    @classmethod
    def validate_image_count(cls, v: list[str]) -> list[str]:
        if len(v) > 5:
            msg = "最多上传5张图片"
            raise ValueError(msg)
        return v


class LostItemListItem(BaseModel):
    id: str
    user_id: str
    item_name: str
    category: str
    description: str | None = None
    lost_time_start: str
    lost_time_end: str
    lost_location: str
    status: str
    review_status: str
    cover_image_url: str | None = None
    created_at: str
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)


class LostItemDetail(BaseModel):
    id: str
    user_id: str
    item_name: str
    category: str
    description: str | None = None
    lost_time_start: str
    lost_time_end: str
    lost_location: str
    subscribe_match: bool
    status: str
    review_status: str
    cover_image_url: str | None = None
    image_urls: list[str] = Field(default_factory=list)
    match_count: int | None = None  # only visible to publisher
    created_at: str
    updated_at: str
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


# ---- Found item ----


class VerifyQuestionInput(BaseModel):
    question_text: str = Field(..., min_length=1, max_length=100)
    answer_keywords: list[str] = Field(..., min_length=1, max_length=10)
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    @field_validator("answer_keywords")
    @classmethod
    def validate_answer_keywords(cls, v: list[str]) -> list[str]:
        if any(len(keyword) < 1 or len(keyword) > 20 for keyword in v):
            msg = "answerKeywords 每个关键词长度必须为 1-20 字"
            raise ValueError(msg)
        return v


class CreateFoundItemRequest(BaseModel):
    item_name: str = Field(..., min_length=1, max_length=100)
    category: str
    description: str | None = Field(None, max_length=500)
    found_time: str
    found_location: str = Field(..., min_length=1, max_length=100)
    custody_type: str
    contact_preference: str
    image_urls: list[str] = Field(default_factory=list)
    verify_questions: list[VerifyQuestionInput] = Field(default_factory=list)
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        if v not in VALID_ITEM_CATEGORIES:
            msg = f"category must be one of {VALID_ITEM_CATEGORIES}"
            raise ValueError(msg)
        return v

    @field_validator("found_time")
    @classmethod
    def validate_found_time_format(cls, v: str) -> str:
        _parse_datetime(v, "foundTime")
        return v

    @field_validator("custody_type")
    @classmethod
    def validate_custody(cls, v: str) -> str:
        if v not in VALID_CUSTODY_TYPES:
            msg = f"custodyType must be one of {VALID_CUSTODY_TYPES}"
            raise ValueError(msg)
        return v

    @field_validator("contact_preference")
    @classmethod
    def validate_contact(cls, v: str) -> str:
        if v not in VALID_CONTACT_PREFERENCES:
            msg = f"contactPreference must be one of {VALID_CONTACT_PREFERENCES}"
            raise ValueError(msg)
        return v

    @field_validator("image_urls")
    @classmethod
    def validate_image_count(cls, v: list[str]) -> list[str]:
        if len(v) > 5:
            msg = "最多上传5张图片"
            raise ValueError(msg)
        return v

    @field_validator("verify_questions")
    @classmethod
    def validate_questions_count(cls, v: list[VerifyQuestionInput]) -> list[VerifyQuestionInput]:
        if len(v) > 3:
            msg = "最多设置3个验证问题"
            raise ValueError(msg)
        return v


class CreateFoundItemResponse(BaseModel):
    id: str
    status: str
    is_sensitive: bool
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class FoundItemListItem(BaseModel):
    id: str
    user_id: str
    item_name: str
    category: str
    description: str | None = None
    found_time: str
    found_location: str
    is_sensitive: bool
    custody_type: str
    contact_preference: str
    status: str
    review_status: str
    cover_image_url: str | None = None
    created_at: str
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)


class VerifyQuestionOutput(BaseModel):
    id: str
    question_text: str  # never expose answer_keywords
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class FoundItemDetail(BaseModel):
    id: str
    user_id: str
    item_name: str
    category: str
    description: str | None = None
    found_time: str
    found_location: str
    is_sensitive: bool
    custody_type: str
    contact_preference: str
    status: str
    review_status: str
    image_urls: list[str] = Field(default_factory=list)
    verify_questions: list[VerifyQuestionOutput] = Field(default_factory=list)
    has_active_claim: bool = False
    created_at: str
    updated_at: str
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


# ---- Status change ----


class ChangeStatusRequest(BaseModel):
    status: str
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in VALID_LOST_STATUSES | VALID_FOUND_STATUSES:
            msg = f"status must be one of {VALID_LOST_STATUSES | VALID_FOUND_STATUSES}"
            raise ValueError(msg)
        return v


class CreateFoundItemsBatchFailure(BaseModel):
    index: int
    error: str
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class CreateFoundItemsBatchRequest(BaseModel):
    items: list[CreateFoundItemRequest] = Field(..., min_length=1, max_length=50)
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class CreateFoundItemsBatchResponse(BaseModel):
    success_ids: list[str] = Field(default_factory=list)
    failures: list[CreateFoundItemsBatchFailure] = Field(default_factory=list)
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


# ---- Query params ----


class LostItemQuery(BaseModel):
    page_no: int = Field(default=1, ge=1, alias="pageNo")
    page_size: int = Field(default=10, ge=1, le=50, alias="pageSize")
    category: str | None = None
    status: str | None = None
    keyword: str | None = None
    location: str | None = None
    sort_by: str = Field(default="CREATED_DESC", alias="sortBy")
    # 默认排除终态 (FOUND/CLOSED); "我的发布" 等需要看历史的页面传 true
    include_closed: bool = Field(default=False, alias="includeClosed")
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    @field_validator("category")
    @classmethod
    def validate_optional_category(cls, v: str | None) -> str | None:
        return _validate_optional_enum(v, VALID_ITEM_CATEGORIES, "category")

    @field_validator("status")
    @classmethod
    def validate_optional_status(cls, v: str | None) -> str | None:
        return _validate_optional_enum(v, VALID_LOST_STATUSES, "status")

    @field_validator("sort_by")
    @classmethod
    def validate_sort_by(cls, v: str) -> str:
        if v not in VALID_SORT_OPTIONS:
            msg = f"sortBy must be one of {VALID_SORT_OPTIONS}"
            raise ValueError(msg)
        return v


class FoundItemQuery(BaseModel):
    page_no: int = Field(default=1, ge=1, alias="pageNo")
    page_size: int = Field(default=10, ge=1, le=50, alias="pageSize")
    category: str | None = None
    status: str | None = None
    keyword: str | None = None
    location: str | None = None
    is_sensitive: bool | None = Field(default=None, alias="isSensitive")
    custody_type: str | None = Field(default=None, alias="custodyType")
    sort_by: str = Field(default="CREATED_DESC", alias="sortBy")
    # 默认排除终态 (RETURNED/CLOSED); "我的发布" 等需要看历史的页面传 true
    include_closed: bool = Field(default=False, alias="includeClosed")
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    @field_validator("category")
    @classmethod
    def validate_optional_category(cls, v: str | None) -> str | None:
        return _validate_optional_enum(v, VALID_ITEM_CATEGORIES, "category")

    @field_validator("status")
    @classmethod
    def validate_optional_status(cls, v: str | None) -> str | None:
        return _validate_optional_enum(v, VALID_FOUND_STATUSES, "status")

    @field_validator("custody_type")
    @classmethod
    def validate_optional_custody_type(cls, v: str | None) -> str | None:
        return _validate_optional_enum(v, VALID_CUSTODY_TYPES, "custodyType")

    @field_validator("sort_by")
    @classmethod
    def validate_sort_by(cls, v: str) -> str:
        if v not in VALID_SORT_OPTIONS:
            msg = f"sortBy must be one of {VALID_SORT_OPTIONS}"
            raise ValueError(msg)
        return v


# ---- File upload ----


class FileUploadResponse(BaseModel):
    url: str
    content_type: str
    size: int
    uploaded_at: str
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
