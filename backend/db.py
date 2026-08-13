import os
import logging
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv
# pyrefly: ignore [missing-import]
from supabase import create_client, Client

logger = logging.getLogger("kadi_teeri.db")

load_dotenv()

url: str = os.environ.get("SUPABASE_URL", "").strip()
key: str = os.environ.get("SUPABASE_KEY", "").strip()

# Automatically fix PGRST125 errors if the user pasted the /rest/v1/ suffix
if url.endswith("/rest/v1/"):
    url = url[:-9]
elif url.endswith("/rest/v1"):
    url = url[:-8]
elif url.endswith("/"):
    url = url[:-1]

supabase: Client | None = None

if url and key:
    supabase = create_client(url, key)
    logger.info("Supabase client initialized successfully.")
else:
    logger.warning("SUPABASE_URL or SUPABASE_KEY is missing. Database operations will fail.")
