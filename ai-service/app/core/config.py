from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """AI service runtime settings.

    Reads from process env and optional `.env` file. All DashScope-related
    fields are optional; when ``DASHSCOPE_API_KEY`` is empty the service
    transparently falls back to the in-process keyword baseline.
    """

    APP_NAME: str = "Xunji AI Service"
    APP_VERSION: str = "0.1.0"

    # ---- DashScope (Alibaba Cloud BaiLian) ----
    DASHSCOPE_API_KEY: str = ""
    DASHSCOPE_BASE_URL: str = "https://dashscope.aliyuncs.com/api/v1"
    # Models. See https://help.aliyun.com/zh/dashscope for the full list.
    DASHSCOPE_TEXT_EMBEDDING_MODEL: str = "text-embedding-v3"
    DASHSCOPE_VL_MODEL: str = "qwen-vl-max"
    # Per-request timeout for outbound calls. Keep short — main backend gives
    # us a 3s budget total.
    DASHSCOPE_TIMEOUT: float = 8.0

    @property
    def use_dashscope(self) -> bool:
        """Auto-detect whether real model calls should be attempted."""
        return bool(self.DASHSCOPE_API_KEY)

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
