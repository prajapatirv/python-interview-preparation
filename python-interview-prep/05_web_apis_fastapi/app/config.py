"""pydantic-settings based configuration: env vars override .env which overrides defaults."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "order-service"
    environment: str = "dev"
    demo_token: str = "demo-token"  # stand-in for a real JWT/OAuth secret; never hardcode in prod
    rate_limit_per_minute: int = 100


@lru_cache
def get_settings() -> Settings:
    return Settings()
