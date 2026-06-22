"""
File import endpoints — multipart upload, history listing.
All endpoints require authentication.

Supported file types: txt, md, csv, json.
Max file size is configured via MAX_UPLOAD_BYTES (default 5 MB).
"""
from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.upload import ImportHistoryOut, ImportResultOut
from app.services import import_service

router = APIRouter(prefix="/imports", tags=["Imports"])

CurrentUser = Annotated[User, Depends(get_current_user)]
DB = Annotated[AsyncSession, Depends(get_db)]


@router.get("/health", summary="Imports router health check")
async def imports_health():
    return {"status": "ok", "router": "imports"}


@router.post(
    "/upload",
    response_model=ImportResultOut,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a file and import it as a note",
    description=(
        "Accepts txt, md, csv, and json files (max 5 MB). "
        "The file is stored on disk, its content is converted to a note, "
        "and an import-history record is created regardless of success or failure."
    ),
)
async def upload_and_import(
    current_user: CurrentUser,
    db: DB,
    file: UploadFile = File(..., description="File to import (.txt, .md, .csv, .json)"),
):
    return await import_service.import_file(db, owner_id=current_user.id, file=file)


@router.get(
    "/history",
    response_model=list[ImportHistoryOut],
    summary="List import history for the current user",
)
async def list_import_history(
    current_user: CurrentUser,
    db: DB,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    return await import_service.list_import_history(
        db, owner_id=current_user.id, limit=limit, offset=offset
    )

