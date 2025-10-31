"""
Конфигурация приложения из переменных окружения.
Использует pydantic-settings для валидации и type safety.
"""
from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import List
import json


class Settings(BaseSettings):
    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"  # Игнорировать лишние поля из .env
    )
    # Database
    DATABASE_URL: str = "sqlite:///./narcomap.db"

    # JWT
    JWT_SECRET_KEY: str = "dev-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # OTP
    OTP_EXPIRE_MINUTES: int = 5
    OTP_LENGTH: int = 6

    # SMS Provider
    SMS_PROVIDER: str = "mock"  # mock | twilio | smsru | custom
    SMS_API_KEY: str = ""
    SMS_API_URL: str = ""

    # App
    APP_NAME: str = "Narcomap API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # CORS
    CORS_ORIGINS: str = '["http://localhost:3000", "http://localhost:8080"]'

    @property
    def cors_origins_list(self) -> List[str]:
        """Парсинг CORS origins из JSON строки"""
        try:
            return json.loads(self.CORS_ORIGINS)
        except:
            return ["*"]

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_HOUR: int = 1000

    # Media Storage
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 10
    ALLOWED_EXTENSIONS: str = '[".jpg", ".jpeg", ".png", ".gif"]'

    @property
    def allowed_extensions_list(self) -> List[str]:
        """Парсинг разрешенных расширений"""
        try:
            return json.loads(self.ALLOWED_EXTENSIONS)
        except:
            return [".jpg", ".jpeg", ".png"]

    # S3 (optional)
    USE_S3: bool = False
    S3_BUCKET_NAME: str = ""
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_ENDPOINT: str = ""
    S3_REGION: str = "us-east-1"

    # Anti-spam
    MAX_MARKERS_PER_USER_PER_DAY: int = 10
    MIN_DISTANCE_BETWEEN_MARKERS_METERS: int = 5

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "./logs/app.log"
    OTP_LOG_FILE: str = "./logs/otp.log"


# Singleton instance
settings = Settings()
