"""
Tags endpoints — create, list, delete tags; attach/detach tags to notes.
All endpoints require authentication and are scoped to the current user.
"""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.tag import NoteTagAttach, TagCreate, TagOut
from app.services import tag_service

router = APIRouter(prefix="/tags", tags=["Tags"])

CurrentUser = Annotated[User, Depends(get_current_user)]
DB = Annotated[AsyncSession, Depends(get_db)]


def _parse_uuid(value: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid ID format."
        )


@router.get("/health", summary="Tags router health check")
async def tags_health():
    return {"status": "ok", "router": "tags"}


@router.post(
    "",
    response_model=TagOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new tag",
)
async def create_tag(payload: TagCreate, current_user: CurrentUser, db: DB):
    return await tag_service.create_tag(db, owner_id=current_user.id, payload=payload)


@router.get("", response_model=list[TagOut], summary="List all tags for the current user")
async def list_tags(current_user: CurrentUser, db: DB):
    return await tag_service.list_tags(db, owner_id=current_user.id)


@router.delete(
    "/{tag_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a tag (also removes it from all notes)",
)
async def delete_tag(tag_id: str, current_user: CurrentUser, db: DB):
    await tag_service.delete_tag(db, owner_id=current_user.id, tag_id=_parse_uuid(tag_id))


# --- Note <-> Tag attachment (nested under /tags for REST clarity) ---

@router.get(
    "/note/{note_id}",
    response_model=list[TagOut],
    summary="List all tags attached to a specific note",
)
async def get_tags_for_note(note_id: str, current_user: CurrentUser, db: DB):
    return await tag_service.get_tags_for_note(
        db, owner_id=current_user.id, note_id=_parse_uuid(note_id)
    )


@router.post(
    "/note/{note_id}",
    response_model=list[TagOut],
    status_code=status.HTTP_200_OK,
    summary="Attach a tag to a note — returns the note's full updated tag list",
)
async def attach_tag(note_id: str, payload: NoteTagAttach, current_user: CurrentUser, db: DB):
    return await tag_service.attach_tag(
        db,
        owner_id=current_user.id,
        note_id=_parse_uuid(note_id),
        tag_id=payload.tag_id,
    )


@router.delete(
    "/note/{note_id}/{tag_id}",
    response_model=list[TagOut],
    summary="Detach a tag from a note — returns the note's updated tag list",
)
async def detach_tag(note_id: str, tag_id: str, current_user: CurrentUser, db: DB):
    return await tag_service.detach_tag(
        db,
        owner_id=current_user.id,
        note_id=_parse_uuid(note_id),
        tag_id=_parse_uuid(tag_id),
    )

