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
