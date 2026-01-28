# config.py
"""
App configuration using pydantic-settings.
"""
import os
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    env: str = "production"
    ssl_cert_path: str = ""
    ssl_key_path: str = ""

    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    @property
    def is_production(self) -> bool:
        return self.env.lower() == "production"

    @property
    def is_development(self) -> bool:
        return self.env.lower() == "development"

@lru_cache()
def get_settings() -> Settings:
    """
    Get application settings from environment variables.
    """
    return Settings(
        env=os.getenv("ENV", "production"),
        ssl_cert_path=os.getenv("SSL_CERT_PATH", ""),
        ssl_key_path=os.getenv("SSL_KEY_PATH", ""),
    )
