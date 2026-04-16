from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "Attendance Insights SaaS"
    environment: str = "development"
    secret_key: str = Field(default="change-me-in-production", alias="SECRET_KEY")
    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/attendance_db",
        alias="DATABASE_URL",
    )
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    ai_provider: str = Field(default="openai", alias="AI_PROVIDER")
    ai_model: str = Field(default="gpt-4o-mini", alias="AI_MODEL")
    session_cookie_name: str = "attendance_session"


@lru_cache
def get_settings() -> Settings:
    return Settings()
