import os
import logging
from dotenv import load_dotenv
from supabase import create_client, Client

logger = logging.getLogger("kadi_teeri.db")

load_dotenv()

url: str = os.environ.get("SUPABASE_URL", "")
key: str = os.environ.get("SUPABASE_KEY", "")

supabase: Client | None = None

if url and key:
    supabase = create_client(url, key)
    logger.info("Supabase client initialized successfully.")
else:
    logger.warning("SUPABASE_URL or SUPABASE_KEY is missing. Database operations will fail.")
