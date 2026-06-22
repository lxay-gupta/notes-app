"""
Import service — handles file validation, storage, content parsing,
note creation, and import-history tracking.

Supported formats and their conversion rules:
  txt / md  → note content = raw decoded text
  csv       → formatted table (header row + data rows) as plain text,
              plus a one-line summary ("N rows, M columns")
  json      → pretty-printed JSON string (indent=2)

No external services, no OCR, no AI processing.
"""
import csv
import io
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging_config import get_logger
from app.models.note import Note
from app.models.upload import ImportHistory, ImportStatus, UploadedFile
from app.schemas.upload import ImportResultOut

logger = get_logger(__name__)

ALLOWED_EXTENSIONS = set(settings.ALLOWED_EXTENSIONS)
MAX_BYTES = settings.MAX_UPLOAD_BYTES


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def _extension(filename: str) -> str:
    """Return the lowercased extension without the leading dot."""
    return Path(filename).suffix.lstrip(".").lower()


def _validate_upload(file: UploadFile, size: int) -> str:
    """
    Validate extension and size. Returns the normalised extension.
    Raises HTTP 400 for bad extension, HTTP 413 for oversized files.
    """
    ext = _extension(file.filename or "")
    if not ext or ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unsupported file type '.{ext}'. "
                f"Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}."
            ),
        )
    if size > MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the {MAX_BYTES // (1024*1024)} MB limit.",
        )
    return ext


# ---------------------------------------------------------------------------
# Content converters — one function per format group
# ---------------------------------------------------------------------------

def _convert_text(raw: bytes) -> tuple[str, str]:
    """
    txt / md: decode to UTF-8 and use as-is.
    Returns (title, content).
    """
    text = raw.decode("utf-8", errors="replace").strip()
    lines = text.splitlines()
    # Use the first non-empty line as the title, falling back to a default.
    title = next((line.strip() for line in lines if line.strip()), "Imported Note")
    title = title.lstrip("#").strip()[:255]
    return title, text


def _convert_csv(raw: bytes) -> tuple[str, str]:
    """
    csv: parse into a plain-text table with a summary header.
    Returns (title, content).
    """
    text = raw.decode("utf-8", errors="replace")
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)

    if not rows:
        return "Imported CSV", "(empty file)"

    header = rows[0]
    data_rows = rows[1:]
    num_cols = len(header)
    num_rows = len(data_rows)

    # Build a plain-text aligned table
    col_widths = [
        max(len(str(header[i])), *(len(str(r[i])) if i < len(r) else 0 for r in data_rows))
        for i in range(num_cols)
    ]

    def fmt_row(cells: list[str]) -> str:
        padded = [str(c).ljust(col_widths[i]) for i, c in enumerate(cells)]
        return "| " + " | ".join(padded) + " |"

    separator = "+-" + "-+-".join("-" * w for w in col_widths) + "-+"
    lines = [
        f"CSV Import — {num_rows} row(s), {num_cols} column(s)",
        "",
        separator,
        fmt_row(header),
        separator,
    ]
    for row in data_rows:
        padded_row = row + [""] * (num_cols - len(row))   # handle ragged rows
        lines.append(fmt_row(padded_row))
    lines.append(separator)

    content = "\n".join(lines)
    title = f"CSV Import ({num_rows} rows)"
    return title, content


def _convert_json(raw: bytes) -> tuple[str, str]:
    """
    json: parse and re-serialise with pretty-printing (indent=2).
    Returns (title, content).
    Falls back to raw text if the file is not valid JSON.
    """
    import logging as _logging
    text = raw.decode("utf-8", errors="replace")
    try:
        parsed = json.loads(text)
        pretty = json.dumps(parsed, indent=2, ensure_ascii=False)
        # Derive a title from top-level keys if it's an object
        if isinstance(parsed, dict):
            keys = list(parsed.keys())
            title = f"JSON Import ({', '.join(str(k) for k in keys[:3])}{'…' if len(keys) > 3 else ''})"
        elif isinstance(parsed, list):
            title = f"JSON Import ({len(parsed)} items)"
        else:
            title = "JSON Import"
        return title, pretty
    except json.JSONDecodeError as exc:
        _logging.getLogger(__name__).warning("Invalid JSON file: %s", exc)
        return "JSON Import (invalid)", text


_CONVERTERS = {
    "txt":  _convert_text,
    "md":   _convert_text,
    "csv":  _convert_csv,
    "json": _convert_json,
}


# ---------------------------------------------------------------------------
# File storage
# ---------------------------------------------------------------------------

def _safe_stored_filename(original: str, file_id: uuid.UUID, ext: str) -> str:
    """
    Build a collision-free filename that doesn't preserve user-supplied paths.
    Format: <uuid>_<sanitised_original>.<ext>
    """
    stem = Path(original).stem
    # Keep only safe characters in the original stem
    safe_stem = "".join(c if c.isalnum() or c in "-_" else "_" for c in stem)[:64]
    return f"{file_id}_{safe_stem}.{ext}"


async def _write_file(content: bytes, stored_filename: str) -> str:
    """Write bytes to UPLOAD_DIR and return the absolute path."""
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    dest = upload_dir / stored_filename
    dest.write_bytes(content)
    return str(dest.resolve())


# ---------------------------------------------------------------------------
# Main import entrypoint
# ---------------------------------------------------------------------------

async def import_file(
    db: AsyncSession,
    owner_id: uuid.UUID,
    file: UploadFile,
) -> ImportResultOut:
    """
    Full import pipeline:
      1. Read & validate
      2. Save to disk
      3. Persist UploadedFile metadata
      4. Create ImportHistory (PENDING)
      5. Convert content → create Note
      6. Update ImportHistory (SUCCESS or FAILED)
      7. Return ImportResultOut
    """
    raw = await file.read()
    ext = _validate_upload(file, len(raw))

    file_id = uuid.uuid4()
    stored_filename = _safe_stored_filename(file.filename or "upload", file_id, ext)
    file_path = await _write_file(raw, stored_filename)

    # Persist file metadata
    uploaded_file_row = UploadedFile(
        id=file_id,
        owner_id=owner_id,
        original_filename=file.filename or "upload",
        stored_filename=stored_filename,
        file_path=file_path,
        file_size_bytes=len(raw),
        content_type=file.content_type or "application/octet-stream",
        extension=ext,
    )
    db.add(uploaded_file_row)
    await db.flush()  # get the ID before creating history row

    # Create history record in PENDING state
    history_row = ImportHistory(
        owner_id=owner_id,
        uploaded_file_id=file_id,
        status=ImportStatus.PENDING.value,
    )
    db.add(history_row)
    await db.flush()

    # Convert content and create note
    note_id: uuid.UUID | None = None
    error_message: str | None = None
    final_status = ImportStatus.SUCCESS

    try:
        converter = _CONVERTERS[ext]
        title, content = converter(raw)

        note = Note(owner_id=owner_id, title=title, content=content)
        db.add(note)
        await db.flush()
        note_id = note.id

        history_row.status = ImportStatus.SUCCESS.value
        history_row.note_id = note_id
        history_row.completed_at = datetime.now(timezone.utc)

    except Exception as exc:  # noqa: BLE001
        logger.exception("Import failed for file %s: %s", stored_filename, exc)
        final_status = ImportStatus.FAILED
        error_message = str(exc)
        history_row.status = ImportStatus.FAILED.value
        history_row.error_message = error_message
        history_row.completed_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(uploaded_file_row)
    await db.refresh(history_row)

    return ImportResultOut(
        uploaded_file=uploaded_file_row,
        import_record=history_row,
        note_id=note_id,
        status=final_status.value,
        message=(
            f"Successfully imported '{file.filename}' as a new note."
            if final_status == ImportStatus.SUCCESS
            else f"Import failed: {error_message}"
        ),
    )


# ---------------------------------------------------------------------------
# History queries
# ---------------------------------------------------------------------------

async def list_import_history(
    db: AsyncSession,
    owner_id: uuid.UUID,
    limit: int = 50,
    offset: int = 0,
) -> list[ImportHistory]:
    result = await db.execute(
        select(ImportHistory)
        .where(ImportHistory.owner_id == owner_id)
        .order_by(ImportHistory.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())
