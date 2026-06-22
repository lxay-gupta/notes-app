"""
Users endpoints — scaffolding only, no business logic implemented yet.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/health", summary="Users router health check")
async def users_health():
    return {"status": "ok", "router": "users"}
