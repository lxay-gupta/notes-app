"""
Unit tests for app.core.security — password hashing and JWT helpers.
These don't require a database connection.
"""
import time

import pytest

from app.core.security import (
    JWTError,
    TokenType,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_password_hash_roundtrip():
    raw = "S3curePassw0rd!"
    hashed = hash_password(raw)
    assert hashed != raw
    assert verify_password(raw, hashed) is True
    assert verify_password("wrong-password", hashed) is False


def test_access_token_roundtrip():
    token, jti, expires_at = create_access_token(subject="user-123")
    payload = decode_token(token)
    assert payload["sub"] == "user-123"
    assert payload["type"] == TokenType.ACCESS.value
    assert payload["jti"] == jti


def test_refresh_token_roundtrip():
    token, jti, expires_at = create_refresh_token(subject="user-456")
    payload = decode_token(token)
    assert payload["sub"] == "user-456"
    assert payload["type"] == TokenType.REFRESH.value
    assert payload["jti"] == jti


def test_decode_invalid_token_raises():
    with pytest.raises(JWTError):
        decode_token("this.is.not-a-valid-jwt")


def test_decode_tampered_token_raises():
    token, _, _ = create_access_token(subject="user-789")
    tampered = token[:-2] + ("aa" if not token.endswith("aa") else "bb")
    with pytest.raises(JWTError):
        decode_token(tampered)
