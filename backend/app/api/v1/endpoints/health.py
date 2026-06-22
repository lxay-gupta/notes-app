"""
Health check endpoint — verifies live DB and Redis connectivity.
"""
from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import settings
from app.db import redis as redis_module
from app.db.session import AsyncSessionLocal

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Detailed health check: DB + Redis")
async def health_check():
    result = {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "checks": {
            "database": "unknown",
            "redis": "unknown",
        },
    }

    # --- Database ---
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        result["checks"]["database"] = "ok"
    except Exception as exc:
        result["checks"]["database"] = f"error: {exc}"
        result["status"] = "degraded"

    # --- Redis ---
    try:
        client = redis_module.redis_client
        if client is None:
            result["checks"]["redis"] = "not initialised"
            result["status"] = "degraded"
        else:
            await client.ping()
            result["checks"]["redis"] = "ok"
    except Exception as exc:
        result["checks"]["redis"] = f"error: {exc}"
        result["status"] = "degraded"

    return result
