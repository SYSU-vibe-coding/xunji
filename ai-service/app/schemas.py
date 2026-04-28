from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

VALID_CATEGORIES = {"CERT", "ELECTRONIC", "DAILY_USE", "BOOK", "OTHER"}


class ClassifyItemRequest(BaseModel):
    image_urls: list[str] = Field(default_factory=list, max_length=5)
    item_name: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    @model_validator(mode="after")
    def validate_has_signal(self) -> "ClassifyItemRequest":
        if not self.image_urls and not self.item_name:
            msg = "imageUrls or itemName is required"
            raise ValueError(msg)
        return self


class ClassifyItemResponse(BaseModel):
    category: str
    tags: list[str]
    confidence: float
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class DetectSensitiveRequest(BaseModel):
    image_url: str = Field(..., min_length=1)
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class DetectSensitiveResponse(BaseModel):
    is_sensitive: bool
    sensitive_type: str | None = None
    masked_image_url: str | None = None
    recognized_fields: dict[str, Any] | None = None
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class MatchItem(BaseModel):
    name: str | None = None
    description: str | None = None
    location: str | None = None
    time: str | None = None
    image_urls: list[str] = Field(default_factory=list, max_length=5)
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class CalculateMatchRequest(BaseModel):
    lost_item: MatchItem
    found_item: MatchItem
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class CalculateMatchResponse(BaseModel):
    image_score: float
    text_score: float
    location_score: float
    time_score: float
    total_score: float
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
