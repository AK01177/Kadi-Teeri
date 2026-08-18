"""
Kadi Teeri Online — Application Configuration Settings

Centralized configuration for database credentials, server host settings,
game defaults, and environment variables.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

# Load environment configuration from .env file
load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Application configuration settings."""

    app_title: str = "Kadi Teeri Online"
    app_version: str = "0.1.0"
    app_description: str = "Multiplayer Indian Trick-Taking Card Game Server"

    port: int = int(os.getenv("PORT", "8000"))
    supabase_url: str = os.getenv("SUPABASE_URL", "").strip()
    supabase_key: str = os.getenv("SUPABASE_KEY", "").strip()

    def get_normalized_supabase_url(self) -> str:
        """Strip trailing API suffixes to prevent PGRST125 errors."""
        url = self.supabase_url
        if url.endswith("/rest/v1/"):
            return url[:-9]
        if url.endswith("/rest/v1"):
            return url[:-8]
        if url.endswith("/"):
            return url[:-1]
        return url


settings = Settings()
