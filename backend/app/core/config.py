from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Xunji Backend"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

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
    ADMIN_ACCOUNT: str = "admin"
    ADMIN_PASSWORD: str = "admin123456"
    ADMIN_PHONE: str = "19900000000"

    # MinIO / Object Storage
    MINIO_ENDPOINT: str = "127.0.0.1:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "xunji"
    MINIO_SECURE: bool = False
    MINIO_URL_EXPIRE_HOURS: int = 168  # 7 days default
    MINIO_SENSITIVE_EXPIRE_HOURS: int = 1  # 1 hour for sensitive

    # AI Service
    AI_SERVICE_BASE_URL: str = "http://127.0.0.1:5000"
    AI_SERVICE_TIMEOUT: float = 3.0

    # SMS (simulated)
    SMS_CODE_TTL_SECONDS: int = 300  # 5 minutes
    SMS_CODE_COOLDOWN_SECONDS: int = 60  # 60s between sends

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
