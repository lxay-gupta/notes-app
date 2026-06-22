"""
Aggregates all v1 endpoint routers into a single APIRouter mounted by main.py.
"""
from fastapi import APIRouter

from app.api.v1.endpoints import auth, health, imports, notes, tags, users

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(notes.router)
api_router.include_router(tags.router)
api_router.include_router(imports.router)
