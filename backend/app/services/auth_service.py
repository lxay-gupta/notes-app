"""
Auth service — business logic for registration, login, token issuance,
refresh-token rotation, and logout.

Kept independent of FastAPI request/response objects so it can be unit
tested or reused outside the HTTP layer.
"""
import hashlib
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_delete, cache_get, cache_set, key_user_profile
from app.core.config import settings
from app.core.security import (
    JWTError,
    TokenType,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.token import TokenResponse
from app.schemas.user import UserCreate, UserOut

_RedisDep = Optional[object]


def _hash_token(raw_token: str) -> str:
    """SHA-256 hex digest of a raw JWT string, for DB-side verification."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


async def register_user(db: AsyncSession, payload: UserCreate) -> User:
    """Create a new user. Raises HTTP 409 if the email is already taken."""
    user = User(
        email=payload.email.lower(),
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists.",
        )
    await db.refresh(user)
    return user


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User:
    """Verify credentials. Raises HTTP 401 if invalid."""
    result = await db.execute(select(User).where(User.email == email.lower()))
    user = result.scalar_one_or_none()

    invalid_credentials = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect email or password.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if user is None or not verify_password(password, user.hashed_password):
        raise invalid_credentials
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="This account is inactive."
        )
    return user


async def issue_tokens(db: AsyncSession, user: User) -> TokenResponse:
    """Issue a new access/refresh token pair and persist the refresh token."""
    access_token, _, _ = create_access_token(subject=str(user.id))
    refresh_token, jti, expires_at = create_refresh_token(subject=str(user.id))

    token_row = RefreshToken(
        user_id=user.id,
        jti=jti,
        token_hash=_hash_token(refresh_token),
        expires_at=expires_at,
    )
    db.add(token_row)
    await db.commit()

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


async def _get_valid_refresh_token_row(db: AsyncSession, raw_token: str) -> RefreshToken:
    """
    Decode + validate a refresh token JWT, then look up and validate its
    corresponding DB row (must exist, be unrevoked, and not expired).
    Raises HTTP 401 on any failure.
    """
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_token(raw_token)
    except JWTError:
        raise unauthorized

    if payload.get("type") != TokenType.REFRESH.value:
        raise unauthorized

    jti = payload.get("jti")
    if not jti:
        raise unauthorized

    result = await db.execute(select(RefreshToken).where(RefreshToken.jti == jti))
    token_row = result.scalar_one_or_none()

    if token_row is None or token_row.revoked:
        raise unauthorized
    if token_row.token_hash != _hash_token(raw_token):
        raise unauthorized
    if token_row.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise unauthorized

    return token_row


async def refresh_tokens(db: AsyncSession, raw_refresh_token: str) -> TokenResponse:
    """
    Validate the given refresh token, revoke it (rotation), and issue a
    brand-new access/refresh pair. Rotation prevents indefinite reuse of a
    single refresh token if it's ever leaked.
    """
    token_row = await _get_valid_refresh_token_row(db, raw_refresh_token)

    result = await db.execute(select(User).where(User.id == token_row.user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer active."
        )

    # Rotate: revoke the old refresh token before issuing a new pair.
    token_row.revoked = True
    db.add(token_row)
    await db.commit()

    return await issue_tokens(db, user)


async def logout_user(db: AsyncSession, raw_refresh_token: str) -> None:
    """
    Revoke the given refresh token. Idempotent-ish: an already-invalid or
    unknown token still results in a 401, since logout should only succeed
    for a token that was genuinely valid for this session.
    """
    token_row = await _get_valid_refresh_token_row(db, raw_refresh_token)
    token_row.revoked = True
    db.add(token_row)
    await db.commit()


async def get_user_by_id(
    db: AsyncSession, user_id: str, redis: _RedisDep = None
) -> User | None:
    if redis:
        cached = await cache_get(redis, key_user_profile(user_id))
        if cached is not None:
            # Reconstruct ORM-like object from cache for dependency use
            # We return None and fall through to DB on cache miss only
            pass  # cache hit returns dict, not ORM — caller uses DB object

    try:
        user_uuid = uuid.UUID(user_id)
    except (ValueError, TypeError):
        return None
    result = await db.execute(select(User).where(User.id == user_uuid))
    user = result.scalar_one_or_none()

    if user and redis:
        user_data = UserOut.model_validate(user).model_dump(mode="json")
        await cache_set(redis, key_user_profile(user_id), user_data, settings.CACHE_TTL_USER_PROFILE)

    return user
