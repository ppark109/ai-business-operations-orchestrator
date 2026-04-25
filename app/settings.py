from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "AI FlowOps"
    app_version: str = "0.1.0"
    database_url: str = "sqlite:///data/runtime/app.sqlite3"
    openai_tracing_enabled: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
