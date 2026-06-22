"""
Note service — business logic for CRUD, pagination, search, archiving, and
soft deletion. Every read/write is scoped to a given `owner_id`, so a user
can never access another user's notes by guessing an ID.

Redis caching is layered transparently on top of all list/search reads.
Any write operation (create, update, delete, archive) invalidates the
owner's note cache entries so subsequent reads hit Postgres fresh.
"""
import json
import math
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import (
    cache_delete,
    cache_get,
    cache_invalidate_notes,
    cache_set,
    key_notes_list,
    key_notes_search,
)
from app.core.config import settings
from app.models.note import Note
from app.schemas.note import NoteCreate, NoteUpdate, PaginatedNotes

# Redis is optional — if None, every operation silently bypasses the cache.
_RedisDep = Optional[object]


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found.")


async def create_note(
    db: AsyncSession,
    owner_id: uuid.UUID,
    payload: NoteCreate,
    redis: _RedisDep = None,
) -> Note:
    note = Note(owner_id=owner_id, title=payload.title, content=payload.content)
    db.add(note)
    await db.commit()
    await db.refresh(note)
    if redis:
        await cache_invalidate_notes(redis, str(owner_id))
    return note


async def _get_owned_note_or_404(
    db: AsyncSession, owner_id: uuid.UUID, note_id: uuid.UUID, include_deleted: bool = False
) -> Note:
    stmt = select(Note).where(Note.id == note_id, Note.owner_id == owner_id)
    if not include_deleted:
        stmt = stmt.where(Note.deleted.is_(False))

    result = await db.execute(stmt)
    note = result.scalar_one_or_none()
    if note is None:
        raise _not_found()
    return note


async def get_note(db: AsyncSession, owner_id: uuid.UUID, note_id: uuid.UUID) -> Note:
    return await _get_owned_note_or_404(db, owner_id, note_id)


async def list_notes(
    db: AsyncSession,
    owner_id: uuid.UUID,
    page: int = 1,
    page_size: int = 20,
    archived: bool | None = None,
    redis: _RedisDep = None,
) -> PaginatedNotes:
    page = max(page, 1)
    page_size = max(min(page_size, 100), 1)

    cache_key = key_notes_list(str(owner_id), page, page_size, archived)
    if redis:
        cached = await cache_get(redis, cache_key)
        if cached is not None:
            return PaginatedNotes(**cached)

    base_filters = [Note.owner_id == owner_id, Note.deleted.is_(False)]
    if archived is not None:
        base_filters.append(Note.archived.is_(archived))

    count_stmt = select(func.count()).select_from(Note).where(*base_filters)
    total = (await db.execute(count_stmt)).scalar_one()

    stmt = (
        select(Note)
        .where(*base_filters)
        .order_by(Note.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    items = result.scalars().all()
    pages = math.ceil(total / page_size) if total else 0

    paginated = PaginatedNotes(items=items, total=total, page=page, page_size=page_size, pages=pages)

    if redis:
        await cache_set(redis, cache_key, paginated.model_dump(mode="json"), settings.CACHE_TTL_NOTES_LIST)

    return paginated


async def search_notes(
    db: AsyncSession,
    owner_id: uuid.UUID,
    query: str,
    page: int = 1,
    page_size: int = 20,
    redis: _RedisDep = None,
) -> PaginatedNotes:
    page = max(page, 1)
    page_size = max(min(page_size, 100), 1)

    cache_key = key_notes_search(str(owner_id), query.strip(), page, page_size)
    if redis:
        cached = await cache_get(redis, cache_key)
        if cached is not None:
            return PaginatedNotes(**cached)

    pattern = f"%{query.strip()}%"
    base_filters = [
        Note.owner_id == owner_id,
        Note.deleted.is_(False),
        or_(Note.title.ilike(pattern), Note.content.ilike(pattern)),
    ]

    count_stmt = select(func.count()).select_from(Note).where(*base_filters)
    total = (await db.execute(count_stmt)).scalar_one()

    stmt = (
        select(Note)
        .where(*base_filters)
        .order_by(Note.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    items = result.scalars().all()
    pages = math.ceil(total / page_size) if total else 0

    paginated = PaginatedNotes(items=items, total=total, page=page, page_size=page_size, pages=pages)

    if redis:
        await cache_set(redis, cache_key, paginated.model_dump(mode="json"), settings.CACHE_TTL_SEARCH)

    return paginated


async def update_note(
    db: AsyncSession,
    owner_id: uuid.UUID,
    note_id: uuid.UUID,
    payload: NoteUpdate,
    redis: _RedisDep = None,
) -> Note:
    note = await _get_owned_note_or_404(db, owner_id, note_id)

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(note, field, value)

    db.add(note)
    await db.commit()
    await db.refresh(note)

    if redis:
        await cache_invalidate_notes(redis, str(owner_id))

    return note


async def soft_delete_note(
    db: AsyncSession,
    owner_id: uuid.UUID,
    note_id: uuid.UUID,
    redis: _RedisDep = None,
) -> None:
    note = await _get_owned_note_or_404(db, owner_id, note_id)
    note.deleted = True
    note.deleted_at = datetime.now(timezone.utc)
    db.add(note)
    await db.commit()

    if redis:
        await cache_invalidate_notes(redis, str(owner_id))


async def set_archived(
    db: AsyncSession,
    owner_id: uuid.UUID,
    note_id: uuid.UUID,
    archived: bool,
    redis: _RedisDep = None,
) -> Note:
    note = await _get_owned_note_or_404(db, owner_id, note_id)
    note.archived = archived
    db.add(note)
    await db.commit()
    await db.refresh(note)

    if redis:
        await cache_invalidate_notes(redis, str(owner_id))

    return note
