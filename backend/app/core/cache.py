"""
Redis caching layer.

Provides a thin, opinionated wrapper around the existing Redis client for
JSON-serialisable values. All cache operations are fire-and-forget on
errors — a Redis failure never breaks a request, it just bypasses the cache.

Key schema (all prefixed with `notes_api:`):
  user_profile:<user_id>
  notes_list:<owner_id>:p<page>:ps<page_size>:arc<archived>
  notes_search:<owner_id>:<query_hash>:p<page>:ps<page_size>
"""
import hashlib
import json
import logging
from typing import Any

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

_PREFIX = "notes_api"


# ---------------------------------------------------------------------------
# Key builders
# ---------------------------------------------------------------------------

def key_user_profile(user_id: str) -> str:
    return f"{_PREFIX}:user_profile:{user_id}"


def key_notes_list(owner_id: str, page: int, page_size: int, archived: bool | None) -> str:
    arc = "none" if archived is None else str(archived).lower()
    return f"{_PREFIX}:notes_list:{owner_id}:p{page}:ps{page_size}:arc{arc}"


def key_notes_search(owner_id: str, query: str, page: int, page_size: int) -> str:
    q_hash = hashlib.md5(query.encode()).hexdigest()[:12]
    return f"{_PREFIX}:notes_search:{owner_id}:{q_hash}:p{page}:ps{page_size}"


def pattern_notes_owner(owner_id: str) -> str:
    """Pattern matching all cached note data for a given owner."""
    return f"{_PREFIX}:notes_*:{owner_id}:*"


# ---------------------------------------------------------------------------
# Core get / set / delete
# ---------------------------------------------------------------------------

async def cache_get(redis: aioredis.Redis, key: str) -> Any | None:
    """Return deserialised value or None on miss / error."""
    try:
        raw = await redis.get(key)
        if raw is None:
            return None
        return json.loads(raw)
    except Exception as exc:  # noqa: BLE001
        logger.warning("cache_get failed for key=%s: %s", key, exc)
        return None


async def cache_set(redis: aioredis.Redis, key: str, value: Any, ttl: int) -> None:
    """Serialise value and store with TTL seconds. Silently swallows errors."""
    try:
        await redis.setex(key, ttl, json.dumps(value, default=str))
    except Exception as exc:  # noqa: BLE001
        logger.warning("cache_set failed for key=%s: %s", key, exc)


async def cache_delete(redis: aioredis.Redis, *keys: str) -> None:
    """Delete one or more keys. Silently swallows errors."""
    try:
        if keys:
            await redis.delete(*keys)
    except Exception as exc:  # noqa: BLE001
        logger.warning("cache_delete failed for keys=%s: %s", keys, exc)


async def cache_invalidate_notes(redis: aioredis.Redis, owner_id: str) -> None:
    """
    Delete every cached notes_list and notes_search entry for this owner.

    Uses SCAN instead of KEYS so it doesn't block the Redis event loop on
    large keyspaces.
    """
    try:
        pattern = f"{_PREFIX}:notes_*:{owner_id}:*"
        cursor = 0
        to_delete: list[str] = []
        while True:
            cursor, keys = await redis.scan(cursor, match=pattern, count=100)
            to_delete.extend(keys)
            if cursor == 0:
                break
        if to_delete:
            await redis.delete(*to_delete)
            logger.debug("cache_invalidate_notes: deleted %d keys for owner=%s", len(to_delete), owner_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("cache_invalidate_notes failed for owner=%s: %s", owner_id, exc)
