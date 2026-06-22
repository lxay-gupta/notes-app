"""
Redis connection setup.

Provides a shared async Redis client and FastAPI lifespan helpers to
initialize/close the connection pool. No caching/business logic is
implemented here — connection plumbing only.
"""
from typing import Optional

import redis.asyncio as redis

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)

redis_client: Optional[redis.Redis] = None


async def init_redis_pool() -> redis.Redis:
    """Create and verify the Redis connection pool. Call on app startup."""
    global redis_client
    redis_client = redis.from_url(
        settings.redis_uri,
        encoding="utf-8",
        decode_responses=True,
    )
    try:
        await redis_client.ping()
        logger.info("Redis connection established at %s", settings.REDIS_HOST)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Redis ping failed on startup: %s", exc)
    return redis_client


async def close_redis_pool() -> None:
    """Close the Redis connection pool. Call on app shutdown."""
    global redis_client
    if redis_client is not None:
        await redis_client.close()
        logger.info("Redis connection closed")


def get_redis() -> redis.Redis:
    """FastAPI dependency to access the shared Redis client."""
    if redis_client is None:
        raise RuntimeError("Redis client has not been initialized yet.")
    return redis_client
