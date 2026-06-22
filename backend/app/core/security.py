"""
Security primitives: password hashing and JWT creation/verification.

This module contains no FastAPI- or DB-specific logic — just pure
cryptographic helpers used by the auth service and dependencies.
"""
import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------
def hash_password(plain_password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------
class TokenType(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"


def _create_token(
    subject: str,
    token_type: TokenType,
    expires_delta: timedelta,
    extra_claims: Optional[dict[str, Any]] = None,
) -> tuple[str, str, datetime]:
    """
    Build a signed JWT.

    Returns (encoded_token, jti, expires_at) so callers (e.g. refresh-token
    persistence) can store the jti/expiry without re-decoding the token.
    """
    now = datetime.now(timezone.utc)
    expire = now + expires_delta
    jti = str(uuid.uuid4())

    to_encode: dict[str, Any] = {
        "sub": subject,
        "type": token_type.value,
        "iat": now,
        "exp": expire,
        "jti": jti,
    }
    if extra_claims:
        to_encode.update(extra_claims)

    encoded = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded, jti, expire


def create_access_token(subject: str) -> tuple[str, str, datetime]:
    """Create a short-lived access token. Returns (token, jti, expires_at)."""
    return _create_token(
        subject=subject,
        token_type=TokenType.ACCESS,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(subject: str) -> tuple[str, str, datetime]:
    """Create a long-lived refresh token. Returns (token, jti, expires_at)."""
    return _create_token(
        subject=subject,
        token_type=TokenType.REFRESH,
        expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )


def decode_token(token: str) -> dict[str, Any]:
    """
    Decode and verify a JWT's signature and expiry.

    Raises jose.JWTError (or a subclass) if the token is invalid, malformed,
    or expired. Callers are expected to catch this.
    """
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])


__all__ = [
    "hash_password",
    "verify_password",
    "TokenType",
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "JWTError",
]
