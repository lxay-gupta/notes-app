"""
Pydantic schemas for Note resources.
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.tag import TagOut


class NoteCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    content: str = Field(default="", max_length=100_000)


class NoteUpdate(BaseModel):
    """All fields optional — only provided fields are updated (PATCH semantics)."""

    title: str | None = Field(default=None, min_length=1, max_length=255)
    content: str | None = Field(default=None, max_length=100_000)


class NoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner_id: uuid.UUID
    title: str
    content: str
    archived: bool
    deleted: bool
    created_at: datetime
    updated_at: datetime
    tags: list["TagOut"] = []


class PaginatedNotes(BaseModel):
    items: list[NoteOut]
    total: int
    page: int
    page_size: int
    pages: int
