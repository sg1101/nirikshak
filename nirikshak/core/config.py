"""Application configuration loaded from environment."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://nirikshak:nirikshak@localhost:5432/nirikshak"
    database_url_sync: str = "postgresql://nirikshak:nirikshak@localhost:5432/nirikshak"
    # OpenCode Go (OpenAI-compatible)
    openai_api_key: str = ""
    openai_base_url: str = "https://opencode.ai/zen/go/v1"
    llm_model: str = "qwen3.6-plus"
    storage_dir: Path = Path("./storage")
    log_level: str = "INFO"
    ocr_languages: list[str] = ["en"]
    confidence_threshold: float = 0.85

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
