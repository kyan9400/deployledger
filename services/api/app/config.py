from functools import lru_cache
from typing import Literal

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="DEPLOYLEDGER_",
        env_file=".env",
        extra="ignore",
    )

    app_name: str = "DeployLedger API"
    environment: Literal["local", "staging", "production"] = "local"
    database_url: str = "sqlite+aiosqlite:///./deployledger.db"
    api_key: SecretStr | None = None
    webhook_secret: SecretStr | None = None
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:4173"]
    # Demo fixtures are opt-in so a production instance never silently receives sample data.
    demo_seed: bool = False
    log_level: str = "INFO"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @property
    def docs_enabled(self) -> bool:
        return self.environment != "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
