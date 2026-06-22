"""
Pydantic schemas for Tag resources.
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TagCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)

    @field_validator("name")
    @classmethod
    def normalise(cls, v: str) -> str:
        """Store tags in lowercase so 'Python' and 'python' are the same."""
        return v.strip().lower()


class TagOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner_id: uuid.UUID
    name: str
    created_at: datetime


class NoteTagAttach(BaseModel):
    tag_id: uuid.UUID
