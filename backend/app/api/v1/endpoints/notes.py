"""
Notes endpoints — full CRUD, search, archive, and soft-delete.
All endpoints require authentication; every query is scoped to the
current user's owner_id.
"""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, get_redis
from app.models.user import User
from app.schemas.note import NoteCreate, NoteOut, NoteUpdate, PaginatedNotes
from app.services import note_service

router = APIRouter(prefix="/notes", tags=["Notes"])

CurrentUser = Annotated[User, Depends(get_current_user)]
DB = Annotated[AsyncSession, Depends(get_db)]
Redis = Annotated[object, Depends(get_redis)]


def _parse_uuid(value: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid ID format.")


@router.get("/health", summary="Notes router health check")
async def notes_health():
    return {"status": "ok", "router": "notes"}


@router.post(
    "",
    response_model=NoteOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new note",
)
async def create_note(payload: NoteCreate, current_user: CurrentUser, db: DB, redis: Redis):
    return await note_service.create_note(db, owner_id=current_user.id, payload=payload, redis=redis)


@router.get(
    "",
    response_model=PaginatedNotes,
    summary="List notes (paginated, optionally filtered by archived state)",
)
async def list_notes(
    current_user: CurrentUser,
    db: DB,
    redis: Redis,
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    archived: bool | None = Query(default=None, description="Filter by archived state"),
):
    return await note_service.list_notes(
        db, owner_id=current_user.id, page=page, page_size=page_size, archived=archived, redis=redis
    )


@router.get(
    "/search",
    response_model=PaginatedNotes,
    summary="Search notes by title and content",
)
async def search_notes(
    current_user: CurrentUser,
    db: DB,
    redis: Redis,
    q: str = Query(min_length=1, max_length=255, description="Search query"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    return await note_service.search_notes(
        db, owner_id=current_user.id, query=q, page=page, page_size=page_size, redis=redis
    )


@router.get("/{note_id}", response_model=NoteOut, summary="Get a single note by ID")
async def get_note(note_id: str, current_user: CurrentUser, db: DB):
    return await note_service.get_note(db, owner_id=current_user.id, note_id=_parse_uuid(note_id))


@router.patch(
    "/{note_id}",
    response_model=NoteOut,
    summary="Update a note (partial — only provided fields are changed)",
)
async def update_note(note_id: str, payload: NoteUpdate, current_user: CurrentUser, db: DB, redis: Redis):
    return await note_service.update_note(
        db, owner_id=current_user.id, note_id=_parse_uuid(note_id), payload=payload, redis=redis
    )


@router.delete(
    "/{note_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a note (hidden, not permanently destroyed)",
)
async def delete_note(note_id: str, current_user: CurrentUser, db: DB, redis: Redis):
    await note_service.soft_delete_note(
        db, owner_id=current_user.id, note_id=_parse_uuid(note_id), redis=redis
    )


@router.post("/{note_id}/archive", response_model=NoteOut, summary="Archive a note")
async def archive_note(note_id: str, current_user: CurrentUser, db: DB, redis: Redis):
    return await note_service.set_archived(
        db, owner_id=current_user.id, note_id=_parse_uuid(note_id), archived=True, redis=redis
    )


@router.post("/{note_id}/unarchive", response_model=NoteOut, summary="Unarchive a note")
async def unarchive_note(note_id: str, current_user: CurrentUser, db: DB, redis: Redis):
    return await note_service.set_archived(
        db, owner_id=current_user.id, note_id=_parse_uuid(note_id), archived=False, redis=redis
    )


