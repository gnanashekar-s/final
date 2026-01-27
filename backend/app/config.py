"""Application configuration and environment variables."""
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = "postgresql://user:pass@localhost:5432/product_to_code"

    # JWT Authentication
    jwt_secret: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"  # Options: gpt-4o, gpt-4-turbo, gpt-4, gpt-3.5-turbo

    # Langfuse Observability
    langfuse_secret_key: Optional[str] = None
    langfuse_public_key: Optional[str] = None
    langfuse_host: str = "https://cloud.langfuse.com"

    # Tavily Web Search (optional)
    tavily_api_key: Optional[str] = None

    # Application
    app_name: str = "Product-to-Code System"
    debug: bool = False
    cors_origins: list[str] = ["http://localhost:8501"]  # Streamlit default port

    # Agent Configuration
    max_retries: int = 3
    checkpoint_dir: str = "./checkpoints"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore"
    }


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
