"""add notes table

Revision ID: 0597a8e9687d
Revises: f59c26ad786c
Create Date: 2026-06-17 13:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0597a8e9687d"
down_revision: Union[str, None] = "f59c26ad786c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "notes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False, server_default=""),
        sa.Column("archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_notes_owner_id"), "notes", ["owner_id"], unique=False)
    op.create_index(op.f("ix_notes_archived"), "notes", ["archived"], unique=False)
    op.create_index(op.f("ix_notes_deleted"), "notes", ["deleted"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_notes_deleted"), table_name="notes")
    op.drop_index(op.f("ix_notes_archived"), table_name="notes")
    op.drop_index(op.f("ix_notes_owner_id"), table_name="notes")
    op.drop_table("notes")
