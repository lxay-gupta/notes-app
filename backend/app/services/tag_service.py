"""
Tag service — create, list, attach and detach tags, all scoped to the
requesting user's owner_id.

Duplicate prevention strategy:
  - Tag names are normalised to lowercase before insert (in the schema
    validator) so 'Python' and 'python' are the same tag.
  - The (owner_id, name) unique constraint on the tags table prevents
    duplicate tag names per user at the DB level.
  - The composite PK (note_id, tag_id) on note_tags prevents the same
    tag from being attached twice; we return 409 if the application
    detects it before the DB does, to give a cleaner error message.
"""
import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.note import Note
from app.models.tag import NoteTag, Tag
from app.schemas.tag import TagCreate


async def _get_owned_tag_or_404(
    db: AsyncSession, owner_id: uuid.UUID, tag_id: uuid.UUID
) -> Tag:
    result = await db.execute(
        select(Tag).where(Tag.id == tag_id, Tag.owner_id == owner_id)
    )
    tag = result.scalar_one_or_none()
    if tag is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found.")
    return tag


async def _get_owned_note_or_404(
    db: AsyncSession, owner_id: uuid.UUID, note_id: uuid.UUID
) -> Note:
    result = await db.execute(
        select(Note).where(
            Note.id == note_id,
            Note.owner_id == owner_id,
            Note.deleted.is_(False),
        )
    )
    note = result.scalar_one_or_none()
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found.")
    return note


async def create_tag(db: AsyncSession, owner_id: uuid.UUID, payload: TagCreate) -> Tag:
    """
    Create a new tag for this user. Returns 409 if a tag with the same
    (normalised) name already exists for the owner.
    """
    tag = Tag(owner_id=owner_id, name=payload.name)
    db.add(tag)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Tag '{payload.name}' already exists.",
        )
    await db.refresh(tag)
    return tag


async def list_tags(db: AsyncSession, owner_id: uuid.UUID) -> list[Tag]:
    """Return all tags owned by this user, ordered alphabetically."""
    result = await db.execute(
        select(Tag)
        .where(Tag.owner_id == owner_id)
        .order_by(Tag.name.asc())
    )
    return list(result.scalars().all())


async def get_tags_for_note(
    db: AsyncSession, owner_id: uuid.UUID, note_id: uuid.UUID
) -> list[Tag]:
    """Return tags attached to a specific note, verifying note ownership."""
    await _get_owned_note_or_404(db, owner_id, note_id)
    result = await db.execute(
        select(Tag)
        .join(NoteTag, NoteTag.tag_id == Tag.id)
        .where(NoteTag.note_id == note_id, Tag.owner_id == owner_id)
        .order_by(Tag.name.asc())
    )
    return list(result.scalars().all())


async def attach_tag(
    db: AsyncSession, owner_id: uuid.UUID, note_id: uuid.UUID, tag_id: uuid.UUID
) -> list[Tag]:
    """
    Attach a tag to a note. Both must belong to the requesting user.
    Returns the note's full updated tag list.
    Raises 409 if the tag is already attached.
    """
    # Verify ownership of both resources before touching note_tags
    await _get_owned_note_or_404(db, owner_id, note_id)
    await _get_owned_tag_or_404(db, owner_id, tag_id)

    # Check for existing association before inserting to give a clean 409
    existing = await db.execute(
        select(NoteTag).where(
            NoteTag.note_id == note_id, NoteTag.tag_id == tag_id
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tag is already attached to this note.",
        )

    association = NoteTag(note_id=note_id, tag_id=tag_id)
    db.add(association)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tag is already attached to this note.",
        )

    return await get_tags_for_note(db, owner_id, note_id)


async def detach_tag(
    db: AsyncSession, owner_id: uuid.UUID, note_id: uuid.UUID, tag_id: uuid.UUID
) -> list[Tag]:
    """
    Remove a tag from a note. Returns the note's updated tag list.
    Raises 404 if the association doesn't exist.
    """
    await _get_owned_note_or_404(db, owner_id, note_id)
    await _get_owned_tag_or_404(db, owner_id, tag_id)

    result = await db.execute(
        select(NoteTag).where(
            NoteTag.note_id == note_id, NoteTag.tag_id == tag_id
        )
    )
    association = result.scalar_one_or_none()
    if association is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag is not attached to this note.",
        )

    await db.delete(association)
    await db.commit()

    return await get_tags_for_note(db, owner_id, note_id)


async def delete_tag(
    db: AsyncSession, owner_id: uuid.UUID, tag_id: uuid.UUID
) -> None:
    """
    Delete a tag entirely. Cascades to note_tags via FK ON DELETE CASCADE,
    so all associations are cleaned up automatically.
    """
    tag = await _get_owned_tag_or_404(db, owner_id, tag_id)
    await db.delete(tag)
    await db.commit()
