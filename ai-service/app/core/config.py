from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """AI service runtime settings.

    Reads from process env and optional `.env` file. Supports both
    DashScope-native and any OpenAI-compatible endpoint (e.g. SiliconFlow).
    When ``DASHSCOPE_API_KEY`` is empty the service transparently falls back
    to the in-process keyword baseline.
    """

    APP_NAME: str = "Xunji AI Service"
    APP_VERSION: str = "0.1.0"

    # Internal API security. Production-like environments must use a random
    # token of at least 32 characters. The bypass is intentionally explicit.
    AI_SERVICE_TOKEN: str = ""
    AI_LOCAL_DEV_MODE: bool = False

    # Comma-separated exact hosts or wildcard suffixes (for example,
    # "objects.example.edu,*.oss.example.com"). Empty means no image URL is
    # accepted, so callers cannot turn the VL provider into an arbitrary fetcher.
    AI_ALLOWED_IMAGE_HOSTS: str = ""
    # Exact hosts only. These are the sole exception for private IPs and
    # single-label container DNS names such as "minio".
    AI_TRUSTED_PRIVATE_IMAGE_HOSTS: str = ""

    # ---- LLM provider (DashScope or any OpenAI-compatible endpoint) ----
    DASHSCOPE_API_KEY: str = ""
    DASHSCOPE_BASE_URL: str = "https://dashscope.aliyuncs.com/api/v1"
    # DashScope-native model names (used for DashScope-specific endpoints).
    DASHSCOPE_TEXT_EMBEDDING_MODEL: str = "text-embedding-v3"
    DASHSCOPE_VL_MODEL: str = "qwen-vl-max"
    # OpenAI-compatible chat model. When set, text similarity uses chat
    # completion instead of embeddings. Takes precedence over embedding.
    LLM_MODEL: str = ""
    # OpenAI-compatible embedding model (optional). Used for text similarity
    # when LLM_MODEL is empty but embeddings are preferred.
    TEXT_EMBEDDING_MODEL: str = ""
    # Per-request timeout for outbound calls. Keep short — main backend gives
    # us a 3s budget total.
    DASHSCOPE_TIMEOUT: float = 8.0

    @model_validator(mode="after")
    def validate_internal_api_security(self) -> "Settings":
        token = self.AI_SERVICE_TOKEN.strip()
        if token and len(token) < 32:
            msg = "AI_SERVICE_TOKEN must contain at least 32 characters"
            raise ValueError(msg)
        if not token and not self.AI_LOCAL_DEV_MODE:
            msg = "AI_SERVICE_TOKEN is required unless AI_LOCAL_DEV_MODE=true"
            raise ValueError(msg)
        self.AI_SERVICE_TOKEN = token
        for host in self.trusted_private_image_hosts:
            if any(char in host for char in ("*", "/", "@", ":")):
                msg = "AI_TRUSTED_PRIVATE_IMAGE_HOSTS must contain exact host names only"
                raise ValueError(msg)
        return self

    @property
    def allowed_image_hosts(self) -> tuple[str, ...]:
        return tuple(
            host.strip().lower().rstrip(".")
            for host in self.AI_ALLOWED_IMAGE_HOSTS.split(",")
            if host.strip()
        )

    @property
    def trusted_private_image_hosts(self) -> tuple[str, ...]:
        return tuple(
            host.strip().lower().rstrip(".")
            for host in self.AI_TRUSTED_PRIVATE_IMAGE_HOSTS.split(",")
            if host.strip()
        )

    @property
    def use_dashscope(self) -> bool:
        """Auto-detect whether real model calls should be attempted."""
        return bool(self.DASHSCOPE_API_KEY)

    @property
    def is_openai_compatible(self) -> bool:
        """True when base URL is not the default DashScope endpoint."""
        return "dashscope.aliyuncs.com" not in self.DASHSCOPE_BASE_URL

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
