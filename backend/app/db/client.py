"""
Kadi Teeri Online — Database Client

Handles initialization and lifecycle management for the Supabase persistent storage client.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.config import settings

if TYPE_CHECKING:
    from supabase import Client

logger = logging.getLogger("kadi_teeri.db")

supabase: Client | None = None

url = settings.get_normalized_supabase_url()
key = settings.supabase_key

if url and key:
    try:
        from supabase import create_client

        supabase = create_client(url, key)
        logger.info("Supabase client initialized successfully.")
    except Exception as err:
        logger.error(f"Failed to initialize Supabase client: {err}")
        supabase = None
else:
    logger.warning("SUPABASE_URL or SUPABASE_KEY missing. Fallback to in-memory mode active.")
