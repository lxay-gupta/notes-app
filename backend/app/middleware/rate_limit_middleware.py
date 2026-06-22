"""
Sliding-window rate limiting middleware.

Applied only to the login and register endpoints.  Every other path is
passed through without any Redis interaction.

Algorithm: per (IP, path) we maintain a sorted set in Redis where each
member is the request timestamp.  On each request:
  1. Remove members older than the window.
  2. Count remaining members.
  3. If count >= limit → 429.
  4. Otherwise add current timestamp and set key TTL.

This avoids the "fixed window burst" problem (someone fires 10 requests
at xx:59, then 10 more at xx+1:00) that a simple counter has.
"""
import time
import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.config import settings
from app.db.redis import redis_client

logger = logging.getLogger(__name__)

# Path → (max_requests, window_seconds)
_RATE_LIMIT_ROUTES: dict[str, tuple[int, int]] = {
    f"{settings.API_V1_PREFIX}/auth/login":    (settings.RATE_LIMIT_LOGIN_MAX,    settings.RATE_LIMIT_LOGIN_WINDOW),
    f"{settings.API_V1_PREFIX}/auth/register": (settings.RATE_LIMIT_REGISTER_MAX, settings.RATE_LIMIT_REGISTER_WINDOW),
}


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path.rstrip("/")
        limit_cfg = _RATE_LIMIT_ROUTES.get(path)

        if limit_cfg is None or request.method not in ("POST", "PUT"):
            return await call_next(request)

        if redis_client is None:
            # Redis not available — degrade gracefully, don't block requests.
            logger.warning("Rate limiter: Redis unavailable, skipping check for %s", path)
            return await call_next(request)

        max_requests, window_seconds = limit_cfg
        ip = _client_ip(request)
        key = f"notes_api:rl:{path}:{ip}"
        now = time.time()
        window_start = now - window_seconds

        try:
            pipe = redis_client.pipeline()
            # Remove timestamps outside the current window
            await pipe.zremrangebyscore(key, "-inf", window_start)
            # Count requests in the window
            await pipe.zcard(key)
            # Add current timestamp as a member (score = member for uniqueness)
            await pipe.zadd(key, {str(now): now})
            # Ensure the key expires after the window
            await pipe.expire(key, window_seconds + 1)
            results = await pipe.execute()

            request_count = results[1]  # zcard result
        except Exception as exc:  # noqa: BLE001
            logger.warning("Rate limiter error for %s/%s: %s", ip, path, exc)
            return await call_next(request)

        if request_count >= max_requests:
            logger.warning("Rate limit exceeded: ip=%s path=%s count=%d", ip, path, request_count)
            return JSONResponse(
                status_code=429,
                content={
                    "detail": f"Too many requests. Maximum {max_requests} per {window_seconds}s.",
                },
                headers={"Retry-After": str(window_seconds)},
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(max_requests)
        response.headers["X-RateLimit-Remaining"] = str(max(0, max_requests - request_count - 1))
        response.headers["X-RateLimit-Window"] = str(window_seconds)
        return response
