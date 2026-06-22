"""
Notes endpoint tests.

Covers: create, get, list (with pagination), search, update (PATCH),
soft-delete, archive/unarchive, and ownership isolation (one user
cannot access another's notes).
"""
import pytest
from httpx import AsyncClient

from tests.conftest import auth_headers, register_and_login


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def create_note(client: AsyncClient, headers: dict, title: str, content: str = "") -> dict:
    resp = await client.post("/api/v1/notes", json={"title": title, "content": content}, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_note_success(client: AsyncClient):
    tokens = await register_and_login(client, "noter1@example.com", "SecurePass1!")
    h = auth_headers(tokens)

    resp = await client.post("/api/v1/notes", json={"title": "My Note", "content": "Hello"}, headers=h)
    assert resp.status_code == 201
    body = resp.json()
    assert body["title"] == "My Note"
    assert body["content"] == "Hello"
    assert body["archived"] is False
    assert body["deleted"] is False
    assert "id" in body
    assert "owner_id" in body
    assert "tags" in body


@pytest.mark.asyncio
async def test_create_note_requires_auth(client: AsyncClient):
    resp = await client.post("/api/v1/notes", json={"title": "Ghost"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_create_note_empty_title_rejected(client: AsyncClient):
    tokens = await register_and_login(client, "noter2@example.com", "SecurePass1!")
    resp = await client.post("/api/v1/notes", json={"title": ""}, headers=auth_headers(tokens))
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_note_default_empty_content(client: AsyncClient):
    tokens = await register_and_login(client, "noter3@example.com", "SecurePass1!")
    resp = await client.post("/api/v1/notes", json={"title": "No Content"}, headers=auth_headers(tokens))
    assert resp.status_code == 201
    assert resp.json()["content"] == ""


# ---------------------------------------------------------------------------
# Get single note
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_note_success(client: AsyncClient):
    tokens = await register_and_login(client, "noter4@example.com", "SecurePass1!")
    h = auth_headers(tokens)
    note = await create_note(client, h, "Fetch Me")

    resp = await client.get(f"/api/v1/notes/{note['id']}", headers=h)
    assert resp.status_code == 200
    assert resp.json()["id"] == note["id"]


@pytest.mark.asyncio
async def test_get_note_not_found(client: AsyncClient):
    tokens = await register_and_login(client, "noter5@example.com", "SecurePass1!")
    import uuid
    resp = await client.get(f"/api/v1/notes/{uuid.uuid4()}", headers=auth_headers(tokens))
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_note_invalid_uuid(client: AsyncClient):
    tokens = await register_and_login(client, "noter6@example.com", "SecurePass1!")
    resp = await client.get("/api/v1/notes/not-a-uuid", headers=auth_headers(tokens))
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_get_note_ownership_isolation(client: AsyncClient):
    """User B must not be able to read User A's note."""
    tokens_a = await register_and_login(client, "noter_a@example.com", "SecurePass1!")
    tokens_b = await register_and_login(client, "noter_b@example.com", "SecurePass1!")

    note = await create_note(client, auth_headers(tokens_a), "Private")
    resp = await client.get(f"/api/v1/notes/{note['id']}", headers=auth_headers(tokens_b))
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# List + pagination
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_notes_empty(client: AsyncClient):
    tokens = await register_and_login(client, "noter7@example.com", "SecurePass1!")
    resp = await client.get("/api/v1/notes", headers=auth_headers(tokens))
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []
    assert body["total"] == 0
    assert body["pages"] == 0


@pytest.mark.asyncio
async def test_list_notes_pagination(client: AsyncClient):
    tokens = await register_and_login(client, "noter8@example.com", "SecurePass1!")
    h = auth_headers(tokens)
    for i in range(5):
        await create_note(client, h, f"Note {i}")

    resp = await client.get("/api/v1/notes?page=1&page_size=2", headers=h)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["items"]) == 2
    assert body["total"] == 5
    assert body["pages"] == 3

    resp2 = await client.get("/api/v1/notes?page=3&page_size=2", headers=h)
    assert len(resp2.json()["items"]) == 1


@pytest.mark.asyncio
async def test_list_notes_only_own(client: AsyncClient):
    """List endpoint must only return the requesting user's notes."""
    tokens_a = await register_and_login(client, "noter_list_a@example.com", "SecurePass1!")
    tokens_b = await register_and_login(client, "noter_list_b@example.com", "SecurePass1!")

    await create_note(client, auth_headers(tokens_a), "A's Note")
    await create_note(client, auth_headers(tokens_a), "A's Note 2")

    resp = await client.get("/api/v1/notes", headers=auth_headers(tokens_b))
    assert resp.json()["total"] == 0


@pytest.mark.asyncio
async def test_list_notes_excludes_deleted(client: AsyncClient):
    tokens = await register_and_login(client, "noter9@example.com", "SecurePass1!")
    h = auth_headers(tokens)
    note = await create_note(client, h, "To Delete")
    await client.delete(f"/api/v1/notes/{note['id']}", headers=h)

    resp = await client.get("/api/v1/notes", headers=h)
    assert resp.json()["total"] == 0


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_search_by_title(client: AsyncClient):
    tokens = await register_and_login(client, "noter10@example.com", "SecurePass1!")
    h = auth_headers(tokens)
    await create_note(client, h, "Python Tips", "some content")
    await create_note(client, h, "JavaScript Guide", "other content")

    resp = await client.get("/api/v1/notes/search?q=python", headers=h)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["title"] == "Python Tips"


@pytest.mark.asyncio
async def test_search_by_content(client: AsyncClient):
    tokens = await register_and_login(client, "noter11@example.com", "SecurePass1!")
    h = auth_headers(tokens)
    await create_note(client, h, "Note A", "contains the word unicorn")
    await create_note(client, h, "Note B", "nothing special here")

    resp = await client.get("/api/v1/notes/search?q=unicorn", headers=h)
    assert resp.json()["total"] == 1


@pytest.mark.asyncio
async def test_search_case_insensitive(client: AsyncClient):
    tokens = await register_and_login(client, "noter12@example.com", "SecurePass1!")
    h = auth_headers(tokens)
    await create_note(client, h, "FastAPI Notes")

    resp = await client.get("/api/v1/notes/search?q=FASTAPI", headers=h)
    assert resp.json()["total"] == 1


@pytest.mark.asyncio
async def test_search_no_results(client: AsyncClient):
    tokens = await register_and_login(client, "noter13@example.com", "SecurePass1!")
    h = auth_headers(tokens)
    await create_note(client, h, "Something Else")

    resp = await client.get("/api/v1/notes/search?q=xyzzy", headers=h)
    assert resp.json()["total"] == 0


@pytest.mark.asyncio
async def test_search_scoped_to_owner(client: AsyncClient):
    tokens_a = await register_and_login(client, "srch_a@example.com", "SecurePass1!")
    tokens_b = await register_and_login(client, "srch_b@example.com", "SecurePass1!")

    await create_note(client, auth_headers(tokens_a), "Secret Note", "classified content")

    resp = await client.get("/api/v1/notes/search?q=classified", headers=auth_headers(tokens_b))
    assert resp.json()["total"] == 0


# ---------------------------------------------------------------------------
# Update (PATCH)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_note_title(client: AsyncClient):
    tokens = await register_and_login(client, "noter14@example.com", "SecurePass1!")
    h = auth_headers(tokens)
    note = await create_note(client, h, "Old Title", "Old Content")

    resp = await client.patch(f"/api/v1/notes/{note['id']}", json={"title": "New Title"}, headers=h)
    assert resp.status_code == 200
    body = resp.json()
    assert body["title"] == "New Title"
    assert body["content"] == "Old Content"  # unchanged


@pytest.mark.asyncio
async def test_update_note_content_only(client: AsyncClient):
    tokens = await register_and_login(client, "noter15@example.com", "SecurePass1!")
    h = auth_headers(tokens)
    note = await create_note(client, h, "Stable Title", "Old Content")

    resp = await client.patch(
        f"/api/v1/notes/{note['id']}", json={"content": "New Content"}, headers=h
    )
    assert resp.json()["title"] == "Stable Title"
    assert resp.json()["content"] == "New Content"


@pytest.mark.asyncio
async def test_update_note_wrong_owner(client: AsyncClient):
    tokens_a = await register_and_login(client, "upd_a@example.com", "SecurePass1!")
    tokens_b = await register_and_login(client, "upd_b@example.com", "SecurePass1!")
    note = await create_note(client, auth_headers(tokens_a), "Protected")

    resp = await client.patch(
        f"/api/v1/notes/{note['id']}", json={"title": "Hacked"}, headers=auth_headers(tokens_b)
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Soft delete
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_soft_delete_note(client: AsyncClient):
    tokens = await register_and_login(client, "noter16@example.com", "SecurePass1!")
    h = auth_headers(tokens)
    note = await create_note(client, h, "Delete Me")

    resp = await client.delete(f"/api/v1/notes/{note['id']}", headers=h)
    assert resp.status_code == 204

    # Deleted note must not appear in GET
    resp2 = await client.get(f"/api/v1/notes/{note['id']}", headers=h)
    assert resp2.status_code == 404


@pytest.mark.asyncio
async def test_delete_wrong_owner(client: AsyncClient):
    tokens_a = await register_and_login(client, "del_a@example.com", "SecurePass1!")
    tokens_b = await register_and_login(client, "del_b@example.com", "SecurePass1!")
    note = await create_note(client, auth_headers(tokens_a), "Mine")

    resp = await client.delete(f"/api/v1/notes/{note['id']}", headers=auth_headers(tokens_b))
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Archive / unarchive
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_archive_note(client: AsyncClient):
    tokens = await register_and_login(client, "noter17@example.com", "SecurePass1!")
    h = auth_headers(tokens)
    note = await create_note(client, h, "Archive Me")

    resp = await client.post(f"/api/v1/notes/{note['id']}/archive", headers=h)
    assert resp.status_code == 200
    assert resp.json()["archived"] is True


@pytest.mark.asyncio
async def test_unarchive_note(client: AsyncClient):
    tokens = await register_and_login(client, "noter18@example.com", "SecurePass1!")
    h = auth_headers(tokens)
    note = await create_note(client, h, "Archived Note")

    await client.post(f"/api/v1/notes/{note['id']}/archive", headers=h)
    resp = await client.post(f"/api/v1/notes/{note['id']}/unarchive", headers=h)
    assert resp.status_code == 200
    assert resp.json()["archived"] is False


@pytest.mark.asyncio
async def test_list_notes_filter_archived(client: AsyncClient):
    tokens = await register_and_login(client, "noter19@example.com", "SecurePass1!")
    h = auth_headers(tokens)
    note_a = await create_note(client, h, "Active")
    note_b = await create_note(client, h, "Archived")
    await client.post(f"/api/v1/notes/{note_b['id']}/archive", headers=h)

    resp_active = await client.get("/api/v1/notes?archived=false", headers=h)
    assert resp_active.json()["total"] == 1
    assert resp_active.json()["items"][0]["id"] == note_a["id"]

    resp_archived = await client.get("/api/v1/notes?archived=true", headers=h)
    assert resp_archived.json()["total"] == 1
    assert resp_archived.json()["items"][0]["id"] == note_b["id"]


@pytest.mark.asyncio
async def test_list_notes_no_filter_returns_all(client: AsyncClient):
    tokens = await register_and_login(client, "noter20@example.com", "SecurePass1!")
    h = auth_headers(tokens)
    n1 = await create_note(client, h, "Active")
    n2 = await create_note(client, h, "To Archive")
    await client.post(f"/api/v1/notes/{n2['id']}/archive", headers=h)

    resp = await client.get("/api/v1/notes", headers=h)
    assert resp.json()["total"] == 2
