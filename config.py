from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
import os


class Settings(BaseSettings):
    APP_NAME: str = "depter"
    DEBUG: bool = False

    db_host: str = os.getenv("DB_HOST", "localhost")
    db_port: int = int(os.getenv("DB_PORT", "5433"))
    db_name: str = os.getenv("DB_NAME", os.getenv("POSTGRES_DB", "depter"))
    db_user: str = os.getenv("DB_USER", os.getenv("POSTGRES_USER", "app"))
    db_pass: str = os.getenv("DB_PASS", os.getenv("POSTGRES_PASSWORD", "app"))
    db_driver: str = "postgresql+asyncpg"

    # AI-провайдеры
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    AI_PROVIDER: str = os.getenv("AI_PROVIDER", "mock")  # "openai" | "gemini" | "mock"

    # Ограничения на загрузку
    MAX_UPLOAD_SIZE_MB: int = 20
    MAX_FILES_PER_UPLOAD: int = 3

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, value):
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "on", "debug", "dev"}:
                return True
            if normalized in {"0", "false", "no", "off", "release", "prod", "production"}:
                return False
        return value

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.db_user}:{self.db_pass}@{self.db_host}:{self.db_port}/{self.db_name}"


settings = Settings()
