"""
Import all SQLAlchemy models here so that Alembic's `autogenerate` can
discover them through `Base.metadata`.

This module intentionally has no logic — it exists purely as a single
import point. As models are added under app/models/, import them below.
"""
from app.db.base_class import Base  # noqa: F401

from app.models.user import User  # noqa: F401
from app.models.refresh_token import RefreshToken  # noqa: F401
from app.models.note import Note  # noqa: F401
from app.models.tag import Tag, NoteTag  # noqa: F401
from app.models.upload import UploadedFile, ImportHistory  # noqa: F401
