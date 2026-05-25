from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

# ---- Auth ----


class LoginRequest(BaseModel):
    login_type: Literal["PHONE_CODE", "PASSWORD"] = Field(..., alias="loginType")
    phone: str | None = Field(None, pattern=r"^\d{11}$")
    account: str | None = Field(None, min_length=3, max_length=64)
    code: str | None = Field(None, pattern=r"^\d{6}$")
    password: str | None = Field(None, min_length=6, max_length=32)
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    @model_validator(mode="after")
    def validate_login_payload(self) -> "LoginRequest":
        if self.login_type == "PHONE_CODE" and (self.phone is None or self.code is None):
            raise ValueError("phone and code are required for PHONE_CODE login")
        if self.login_type == "PASSWORD" and (
            self.password is None or (self.phone is None and self.account is None)
        ):
            raise ValueError("account/phone and password are required for PASSWORD login")
        return self


class RegisterRequest(BaseModel):
    phone: str = Field(..., pattern=r"^\d{11}$")
    code: str = Field(..., pattern=r"^\d{6}$")
    password: str = Field(..., min_length=6, max_length=32)
    nickname: str = Field(..., min_length=2, max_length=20)
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class SmsCodeRequest(BaseModel):
    phone: str = Field(..., pattern=r"^\d{11}$")
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class SmsCodeResponse(BaseModel):
    sent: bool
    expires_in: int
    # Local development returns the code until a real SMS provider is configured.
    debug_code: str
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class LoginUserData(BaseModel):
    id: str
    nickname: str
    avatar_url: str | None = None
    role: str
    cert_status: str
    credit_score: int
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)


class LoginResponse(BaseModel):
    token: str
    user: LoginUserData
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


# ---- Current user (JWT-derived, lightweight) ----


class CurrentUser(BaseModel):
    id: str
    role: str
    status: str


# ---- Profile ----


class UserProfileResponse(BaseModel):
    id: str
    phone: str  # masked
    nickname: str
    avatar_url: str | None = None
    role: str
    cert_status: str
    campus_id: str | None = None
    real_name: str | None = None
    credit_score: int
    status: str
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)


class UpdateProfileRequest(BaseModel):
    nickname: str | None = Field(None, min_length=2, max_length=20)
    avatar_url: str | None = Field(None, alias="avatarUrl")
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


# ---- Certification ----


class CertificationRequest(BaseModel):
    campus_id: str = Field(..., min_length=4, max_length=20, pattern=r"^[A-Za-z0-9]+$")
    real_name: str = Field(..., min_length=2, max_length=20)
    document_image_url: str = Field(..., min_length=1)
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class CertificationResponse(BaseModel):
    id: str
    campus_id: str
    real_name: str | None = None
    document_image_url: str
    review_status: str
    review_comment: str | None = None
    reviewed_at: str | None = None
    created_at: str
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
