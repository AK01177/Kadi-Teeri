"""
Redis Client Manager
"""
import os
import logging
from redis.asyncio import Redis, from_url

logger = logging.getLogger("kadi_teeri.redis")

# A global redis client instance
redis_client: Redis | None = None

async def init_redis():
    """Initialize the global Redis connection."""
    global redis_client
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
    logger.info(f"Connecting to Redis at {redis_url}...")
    try:
        redis_client = from_url(redis_url, decode_responses=True)
        await redis_client.ping()
        logger.info("Connected to Redis successfully.")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        redis_client = None

async def close_redis():
    """Close the global Redis connection."""
    global redis_client
    if redis_client:
        await redis_client.close()
        logger.info("Closed Redis connection.")
