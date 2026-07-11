import pytest
from app.core.config import Settings
from pydantic import ValidationError


def test_settings_require_token_outside_local_dev() -> None:
    with pytest.raises(ValidationError, match="AI_SERVICE_TOKEN is required"):
        Settings(AI_SERVICE_TOKEN="", AI_LOCAL_DEV_MODE=False, _env_file=None)


def test_settings_reject_short_token() -> None:
    with pytest.raises(ValidationError, match="at least 32 characters"):
        Settings(AI_SERVICE_TOKEN="too-short", AI_LOCAL_DEV_MODE=False, _env_file=None)


def test_settings_allow_explicit_local_dev_without_token() -> None:
    local = Settings(AI_SERVICE_TOKEN="", AI_LOCAL_DEV_MODE=True, _env_file=None)
    assert local.AI_LOCAL_DEV_MODE is True
    assert local.AI_SERVICE_TOKEN == ""


def test_private_image_allowlist_rejects_wildcards() -> None:
    with pytest.raises(ValidationError, match="exact host names"):
        Settings(
            AI_SERVICE_TOKEN="",
            AI_LOCAL_DEV_MODE=True,
            AI_TRUSTED_PRIVATE_IMAGE_HOSTS="*.internal",
            _env_file=None,
        )
