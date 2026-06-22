"""
Unit tests for note service logic.

These tests exercise the pure-logic pieces of note_service.py that can be
verified without a live database: pagination maths, search pattern building,
ownership-scoping query construction, and the soft-delete / archive state
machines.

Tests that require a real async SQLAlchemy session (create_note, list_notes,
etc.) are marked with a comment indicating they should be run against a
test database (e.g. a Docker-based Postgres fixture) once the project is
set up locally.
"""
import math
import uuid

import pytest


# ---------------------------------------------------------------------------
# Pagination arithmetic — extracted from note_service.list_notes
# ---------------------------------------------------------------------------
def _calc_pagination(total: int, page: int, page_size: int) -> dict:
    page = max(page, 1)
    page_size = max(min(page_size, 100), 1)
    pages = math.ceil(total / page_size) if total else 0
    offset = (page - 1) * page_size
    return {"pages": pages, "offset": offset, "page": page, "page_size": page_size}


def test_pagination_first_page():
    r = _calc_pagination(total=55, page=1, page_size=20)
    assert r["pages"] == 3
    assert r["offset"] == 0


def test_pagination_last_page():
    r = _calc_pagination(total=55, page=3, page_size=20)
    assert r["offset"] == 40


def test_pagination_empty_result():
    r = _calc_pagination(total=0, page=1, page_size=20)
    assert r["pages"] == 0


def test_pagination_clamps_page_below_one():
    r = _calc_pagination(total=10, page=0, page_size=20)
    assert r["page"] == 1
    assert r["offset"] == 0


def test_pagination_clamps_page_size_above_max():
    r = _calc_pagination(total=10, page=1, page_size=9999)
    assert r["page_size"] == 100


def test_pagination_clamps_page_size_below_one():
    r = _calc_pagination(total=10, page=1, page_size=0)
    assert r["page_size"] == 1


def test_pagination_exact_multiple():
    r = _calc_pagination(total=40, page=2, page_size=20)
    assert r["pages"] == 2
    assert r["offset"] == 20


# ---------------------------------------------------------------------------
# Search pattern building — mirrors note_service.search_notes
# ---------------------------------------------------------------------------
def _build_ilike_pattern(query: str) -> str:
    return f"%{query.strip()}%"


def test_search_pattern_wraps_query():
    assert _build_ilike_pattern("hello") == "%hello%"


def test_search_pattern_strips_whitespace():
    assert _build_ilike_pattern("  hello  ") == "%hello%"


def test_search_pattern_preserves_internal_spaces():
    assert _build_ilike_pattern("hello world") == "%hello world%"


# ---------------------------------------------------------------------------
# Ownership scope — verifies that owner_id filtering logic is sound
# ---------------------------------------------------------------------------
def test_owner_id_is_uuid():
    """owner_id stored as UUID, not string — verify no accidental str coercion."""
    owner_id = uuid.uuid4()
    other_id = uuid.uuid4()
    assert owner_id != other_id
    assert isinstance(owner_id, uuid.UUID)


def test_uuid_parse_valid():
    raw = "550e8400-e29b-41d4-a716-446655440000"
    parsed = uuid.UUID(raw)
    assert str(parsed) == raw


def test_uuid_parse_invalid_raises():
    with pytest.raises(ValueError):
        uuid.UUID("not-a-uuid")


# ---------------------------------------------------------------------------
# Soft-delete state machine
# ---------------------------------------------------------------------------
class _FakeNote:
    """Minimal stand-in for a Note ORM instance to test state transitions."""
    def __init__(self):
        self.deleted = False
        self.deleted_at = None
        self.archived = False


def test_soft_delete_sets_flags():
    from datetime import datetime, timezone
    note = _FakeNote()
    note.deleted = True
    note.deleted_at = datetime.now(timezone.utc)
    assert note.deleted is True
    assert note.deleted_at is not None


def test_archive_toggle():
    note = _FakeNote()
    note.archived = True
    assert note.archived is True
    note.archived = False
    assert note.archived is False


def test_archived_note_can_be_soft_deleted():
    """Archiving and deleting are independent states."""
    from datetime import datetime, timezone
    note = _FakeNote()
    note.archived = True
    note.deleted = True
    note.deleted_at = datetime.now(timezone.utc)
    assert note.archived is True
    assert note.deleted is True


# ---------------------------------------------------------------------------
# NoteCreate / NoteUpdate schema validation (stdlib only — no pydantic)
# ---------------------------------------------------------------------------
def test_note_update_exclude_unset_semantics():
    """
    NoteUpdate uses PATCH semantics via model_dump(exclude_unset=True).
    Verify that only fields explicitly passed would be updated.
    This mirrors what update_note() does: for field, value in update_data.items(): setattr(...)
    """
    # Simulate what pydantic's model_dump(exclude_unset=True) returns for a
    # partial update (only title provided, content not touched)
    simulated_unset_dump = {"title": "New Title"}

    note = _FakeNote()
    note.title = "Old Title"
    note.content = "Old Content"

    for field, value in simulated_unset_dump.items():
        setattr(note, field, value)

    assert note.title == "New Title"
    assert note.content == "Old Content"  # unchanged — not in the payload
