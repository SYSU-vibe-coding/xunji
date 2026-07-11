from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Xunji Backend"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    CORS_ALLOWED_ORIGINS: str = ""

    # Database
    DB_HOST: str = "127.0.0.1"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = ""
    DB_NAME: str = "xunji"
    DB_ECHO: bool = False

    @property
    def database_url(self) -> str:
        return (
            f"mysql+asyncmy://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            "?charset=utf8mb4"
        )

    # For unit tests with aiosqlite
    DATABASE_URL_OVERRIDE: str | None = None

    # JWT
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_DAYS: int = 7

    # Bootstrap admin account for local/first deployment.
    BOOTSTRAP_ADMIN_ENABLED: bool = False
    ADMIN_ACCOUNT: str = "admin"
    ADMIN_PASSWORD: str = "admin123456"
    ADMIN_PHONE: str = "19900000000"

    # MinIO / Object Storage
    MINIO_ENDPOINT: str = "127.0.0.1:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "xunji"
    MINIO_REGION: str = "us-east-1"
    MINIO_SECURE: bool = False
    MINIO_URL_EXPIRE_HOURS: int = 168  # 7 days default
    MINIO_SENSITIVE_EXPIRE_HOURS: int = 1  # 1 hour for sensitive
    MINIO_AI_URL_EXPIRE_MINUTES: int = 10
    MINIO_MAX_IMAGE_PIXELS: int = 25_000_000
    # Browser-reachable MinIO endpoint used only to generate presigned URLs.
    # Objects remain private and this URL is never persisted.
    # Empty -> auto-derive from MINIO_ENDPOINT + MINIO_SECURE.
    MINIO_PUBLIC_BASE_URL: str = ""

    @property
    def minio_public_base_url(self) -> str:
        if self.MINIO_PUBLIC_BASE_URL:
            return self.MINIO_PUBLIC_BASE_URL.rstrip("/")
        scheme = "https" if self.MINIO_SECURE else "http"
        return f"{scheme}://{self.MINIO_ENDPOINT}"

    # AI Service
    AI_SERVICE_BASE_URL: str = "http://127.0.0.1:5000"
    AI_SERVICE_TIMEOUT: float = 3.0
    AI_SERVICE_TOKEN: str = ""

    # Match auto-trigger. 0 = disabled (admin must trigger manually).
    MATCH_AUTO_INTERVAL_MINUTES: int = 0
    MATCH_JOB_MAX_CONCURRENCY: int = 8
    MATCH_RECALCULATE_MAX_CANDIDATES: int = 100

    # Durable item outbox runner.
    DURABLE_JOB_POLL_SECONDS: float = 1.0
    DURABLE_JOB_MAX_ATTEMPTS: int = 5
    DURABLE_JOB_RETRY_BASE_SECONDS: float = 5.0
    DURABLE_JOB_LOCK_TIMEOUT_SECONDS: int = 300
    SENSITIVE_JOB_MAX_CONCURRENCY: int = 3

    # SMS (simulated)
    SMS_DEBUG_ENABLED: bool = False
    SMS_DEMO_PHONES: str = ""
    SMS_CODE_TTL_SECONDS: int = 300  # 5 minutes
    SMS_CODE_COOLDOWN_SECONDS: int = 60  # 60s between sends

    @property
    def sms_demo_phones(self) -> set[str]:
        return {phone.strip() for phone in self.SMS_DEMO_PHONES.split(",") if phone.strip()}

    @property
    def cors_allowed_origins(self) -> list[str]:
        origins = [origin.strip().rstrip("/") for origin in self.CORS_ALLOWED_ORIGINS.split(",")]
        return [origin for origin in origins if origin]

    def validate_startup_security(self) -> None:
        if "*" in self.cors_allowed_origins:
            raise RuntimeError("CORS_ALLOWED_ORIGINS must be an explicit origin allowlist")
        if self.DEBUG:
            return
        insecure: list[str] = []
        if self.JWT_SECRET_KEY == "change-me-in-production":
            insecure.append("JWT_SECRET_KEY")
        if self.ADMIN_PASSWORD == "admin123456":
            insecure.append("ADMIN_PASSWORD")
        if insecure:
            names = ", ".join(insecure)
            raise RuntimeError(
                f"Refusing to start with insecure default settings: {names}. "
                "Set unique values, or explicitly enable DEBUG for local development."
            )

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
