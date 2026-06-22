"""
Auth endpoint tests.

Covers: register, login, token refresh, logout, /me, and security edge
cases (duplicate email, bad credentials, token reuse after logout).
"""
import pytest
from httpx import AsyncClient

from tests.conftest import auth_headers, register_and_login


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    resp = await client.post("/api/v1/auth/register", json={
        "email": "alice@example.com",
        "password": "SecurePass1!",
        "full_name": "Alice",
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "alice@example.com"
    assert body["full_name"] == "Alice"
    assert "hashed_password" not in body
    assert "id" in body


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    payload = {"email": "bob@example.com", "password": "SecurePass1!"}
    await client.post("/api/v1/auth/register", json=payload)
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 409
    assert "already exists" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_register_email_case_insensitive(client: AsyncClient):
    """alice@EXAMPLE.COM and alice@example.com must collide."""
    await client.post("/api/v1/auth/register", json={
        "email": "charlie@example.com", "password": "SecurePass1!",
    })
    resp = await client.post("/api/v1/auth/register", json={
        "email": "CHARLIE@EXAMPLE.COM", "password": "SecurePass1!",
    })
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_register_password_too_short(client: AsyncClient):
    resp = await client.post("/api/v1/auth/register", json={
        "email": "short@example.com", "password": "abc",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_register_invalid_email(client: AsyncClient):
    resp = await client.post("/api/v1/auth/register", json={
        "email": "not-an-email", "password": "SecurePass1!",
    })
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    await client.post("/api/v1/auth/register", json={
        "email": "diana@example.com", "password": "SecurePass1!",
    })
    resp = await client.post("/api/v1/auth/login", json={
        "email": "diana@example.com", "password": "SecurePass1!",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    await client.post("/api/v1/auth/register", json={
        "email": "eve@example.com", "password": "SecurePass1!",
    })
    resp = await client.post("/api/v1/auth/login", json={
        "email": "eve@example.com", "password": "WrongPassword!",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_email(client: AsyncClient):
    resp = await client.post("/api/v1/auth/login", json={
        "email": "nobody@example.com", "password": "SecurePass1!",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_case_insensitive_email(client: AsyncClient):
    """Login with uppercase email should work after registering with lowercase."""
    await client.post("/api/v1/auth/register", json={
        "email": "frank@example.com", "password": "SecurePass1!",
    })
    resp = await client.post("/api/v1/auth/login", json={
        "email": "FRANK@EXAMPLE.COM", "password": "SecurePass1!",
    })
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# /me
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_me_authenticated(client: AsyncClient):
    tokens = await register_and_login(client, "grace@example.com", "SecurePass1!")
    resp = await client.get("/api/v1/auth/me", headers=auth_headers(tokens))
    assert resp.status_code == 200
    assert resp.json()["email"] == "grace@example.com"


@pytest.mark.asyncio
async def test_get_me_no_token(client: AsyncClient):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_me_invalid_token(client: AsyncClient):
    resp = await client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer not.a.valid.token"}
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_me_malformed_header(client: AsyncClient):
    resp = await client.get(
        "/api/v1/auth/me", headers={"Authorization": "NotBearer token"}
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Token refresh
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_refresh_success(client: AsyncClient):
    tokens = await register_and_login(client, "henry@example.com", "SecurePass1!")
    resp = await client.post("/api/v1/auth/refresh", json={
        "refresh_token": tokens["refresh_token"],
    })
    assert resp.status_code == 200
    new_tokens = resp.json()
    assert "access_token" in new_tokens
    assert "refresh_token" in new_tokens
    # New tokens must differ from old ones (rotation)
    assert new_tokens["access_token"] != tokens["access_token"]
    assert new_tokens["refresh_token"] != tokens["refresh_token"]


@pytest.mark.asyncio
async def test_refresh_reuse_old_token_fails(client: AsyncClient):
    """After rotation, the old refresh token must be revoked."""
    tokens = await register_and_login(client, "irene@example.com", "SecurePass1!")
    old_refresh = tokens["refresh_token"]

    # First rotation
    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert resp.status_code == 200

    # Second use of the same old token must fail
    resp2 = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert resp2.status_code == 401


@pytest.mark.asyncio
async def test_refresh_with_access_token_fails(client: AsyncClient):
    """Submitting an access token to /refresh must be rejected."""
    tokens = await register_and_login(client, "jake@example.com", "SecurePass1!")
    resp = await client.post("/api/v1/auth/refresh", json={
        "refresh_token": tokens["access_token"],  # wrong token type
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_refresh_invalid_token_fails(client: AsyncClient):
    resp = await client.post("/api/v1/auth/refresh", json={
        "refresh_token": "garbage.token.value",
    })
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_logout_success(client: AsyncClient):
    tokens = await register_and_login(client, "karen@example.com", "SecurePass1!")
    resp = await client.post("/api/v1/auth/logout", json={
        "refresh_token": tokens["refresh_token"],
    })
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_logout_revokes_refresh_token(client: AsyncClient):
    """After logout, the refresh token must no longer be usable."""
    tokens = await register_and_login(client, "leo@example.com", "SecurePass1!")
    await client.post("/api/v1/auth/logout", json={"refresh_token": tokens["refresh_token"]})

    resp = await client.post("/api/v1/auth/refresh", json={
        "refresh_token": tokens["refresh_token"],
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_logout_invalid_token_fails(client: AsyncClient):
    resp = await client.post("/api/v1/auth/logout", json={
        "refresh_token": "not.a.real.token",
    })
    assert resp.status_code == 401
