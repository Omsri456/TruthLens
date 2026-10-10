"""
TruthLens AI — Core configuration module.

Reads all settings from environment variables with sensible defaults.
"""

import os
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application-wide settings loaded from environment variables."""

    # --- App ---
    app_env: str = Field(default="development", alias="APP_ENV")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    frontend_url: str = Field(default="http://localhost:5173", alias="FRONTEND_URL")

    # --- LLM (Gemini) ---
    gemini_api_key: Optional[str] = Field(default=None, alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-2.5-flash", alias="GEMINI_MODEL")

    # --- Web Search (Google Custom Search) ---
    google_search_api_key: Optional[str] = Field(default=None, alias="GOOGLE_SEARCH_API_KEY")
    google_search_engine_id: Optional[str] = Field(default=None, alias="GOOGLE_SEARCH_ENGINE_ID")

    # --- Database ---
    database_url: str = Field(default="sqlite:///./truthlens.db", alias="DATABASE_URL")

    # --- Upload Limits ---
    max_upload_size_mb: int = Field(default=10, alias="MAX_UPLOAD_SIZE_MB")
    max_audio_duration_seconds: int = Field(default=300, alias="MAX_AUDIO_DURATION_SECONDS")
    max_pdf_pages: int = Field(default=50, alias="MAX_PDF_PAGES")

    # --- Security ---
    cors_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173",
        alias="CORS_ORIGINS",
    )

    # --- Paths ---
    base_dir: Path = Field(default_factory=lambda: Path(__file__).resolve().parent.parent.parent)
    uploads_dir: Optional[Path] = Field(default=None)

    def model_post_init(self, __context) -> None:
        if self.uploads_dir is None:
            self.uploads_dir = self.base_dir / "uploads"
        self.uploads_dir.mkdir(parents=True, exist_ok=True)

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def is_search_configured(self) -> bool:
        return bool(self.google_search_api_key and self.google_search_engine_id)

    @property
    def is_llm_configured(self) -> bool:
        return bool(self.gemini_api_key)

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


# Singleton instance
settings = Settings()
