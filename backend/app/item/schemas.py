from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel

# ---- Enums for validation ----
VALID_ITEM_CATEGORIES = {"CERT", "ELECTRONIC", "DAILY_USE", "BOOK", "OTHER"}
VALID_LOST_STATUSES = {"SEARCHING", "FOUND", "CLOSED"}
VALID_FOUND_STATUSES = {"PENDING", "CLAIMING", "RETURNED", "CLOSED"}
VALID_CUSTODY_TYPES = {"SELF", "SECURITY", "OFFICE"}
VALID_CONTACT_PREFERENCES = {"IN_APP", "PHONE"}
VALID_BIZ_TYPES = {"LOST", "FOUND", "CLAIM_PROOF", "CERT"}
VALID_SORT_OPTIONS = {"CREATED_DESC", "CREATED_ASC"}


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


# ---- Query params ----


class LostItemQuery(BaseModel):
    page_no: int = Field(default=1, ge=1, alias="pageNo")
    page_size: int = Field(default=10, ge=1, le=50, alias="pageSize")
    category: str | None = None
    status: str | None = None
    keyword: str | None = None
    location: str | None = None
    sort_by: str = Field(default="CREATED_DESC", alias="sortBy")
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


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
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


# ---- File upload ----


class FileUploadResponse(BaseModel):
    url: str
    content_type: str
    size: int
    uploaded_at: str
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
