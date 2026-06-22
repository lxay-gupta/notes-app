"""
Tag and NoteTag (association) ORM models.

Tags are owned per-user — "python" for user A is a different tag than
"python" for user B. This keeps tag management simple and avoids
cross-user tag namespace collisions.

NoteTag is the many-to-many association table. Its composite primary key
(note_id, tag_id) is the sole uniqueness constraint — enforced at the DB
level so no application-side duplicate check is needed.
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class NoteTag(Base):
    """
    Association table for the Note <-> Tag many-to-many relationship.
    Composite PK prevents the same tag from being attached to the same
    note twice.
    """

    __tablename__ = "note_tags"

    note_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("notes.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Tag(Base):
    __tablename__ = "tags"

    __table_args__ = (
        # One tag name per user — case-sensitive at DB level; normalised to
        # lowercase in the service layer before insert/lookup.
        UniqueConstraint("owner_id", "name", name="uq_tags_owner_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(64), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    notes: Mapped[list["Note"]] = relationship(
        "Note", secondary="note_tags", back_populates="tags"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Tag id={self.id} owner_id={self.owner_id} name={self.name!r}>"
