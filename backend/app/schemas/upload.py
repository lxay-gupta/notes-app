"""
Pydantic schemas for file upload and import history resources.
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UploadedFileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner_id: uuid.UUID
    original_filename: str
    file_size_bytes: int
    content_type: str
    extension: str
    created_at: datetime


class ImportHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner_id: uuid.UUID
    uploaded_file_id: uuid.UUID
    note_id: uuid.UUID | None
    status: str
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None


class ImportResultOut(BaseModel):
    """Single response returned from the import endpoint."""

    uploaded_file: UploadedFileOut
    import_record: ImportHistoryOut
    note_id: uuid.UUID | None
    status: str
    message: str
