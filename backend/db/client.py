"""
Kadi Teeri Online — Database Client

Handles initialization and lifecycle management for the Supabase persistent storage client.
Normalizes API endpoint URLs to prevent common routing configuration issues.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from dotenv import load_dotenv
from supabase import Client, create_client

logger = logging.getLogger("kadi_teeri.db")

# Load environment configuration from .env if present
load_dotenv()

url: str = os.environ.get("SUPABASE_URL", "").strip()
key: str = os.environ.get("SUPABASE_KEY", "").strip()

# Normalize REST API endpoint URL (strip /rest/v1 trailing paths if provided)
if url.endswith("/rest/v1/"):
    url = url[:-9]
elif url.endswith("/rest/v1"):
    url = url[:-8]
elif url.endswith("/"):
    url = url[:-1]

# Initialize global Supabase client instance
supabase: Optional[Client] = None

if url and key:
    try:
        supabase = create_client(url, key)
        logger.info("Supabase client initialized successfully.")
    except Exception as err:
        logger.error(f"Failed to initialize Supabase client: {err}")
        supabase = None
else:
    logger.warning("SUPABASE_URL or SUPABASE_KEY missing. Fallback to in-memory mode active.")
