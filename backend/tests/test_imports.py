"""
File import endpoint tests.

Covers: all four supported formats (txt, md, csv, json), rejection of
unsupported types, oversized file handling, import history listing, and
that every import creates a note owned by the requesting user.
"""
import io
import json

import pytest
from httpx import AsyncClient

from tests.conftest import auth_headers, register_and_login


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _upload(client: AsyncClient, headers: dict, filename: str, content: bytes, ct: str):
    """Convenience: POST multipart file upload."""
    return client.post(
        "/api/v1/imports/upload",
        headers=headers,
        files={"file": (filename, io.BytesIO(content), ct)},
    )


# ---------------------------------------------------------------------------
# txt
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_import_txt_success(client: AsyncClient):
    tokens = await register_and_login(client, "imp_txt@example.com", "SecurePass1!")
    h = auth_headers(tokens)

    content = b"My Plain Note\n\nThis is the body of the text note."
    resp = await _upload(client, h, "note.txt", content, "text/plain")

    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "success"
    assert body["note_id"] is not None
    assert "note.txt" in body["message"]
    assert body["uploaded_file"]["extension"] == "txt"
    assert body["uploaded_file"]["file_size_bytes"] == len(content)


@pytest.mark.asyncio
async def test_import_txt_title_from_first_line(client: AsyncClient):
    tokens = await register_and_login(client, "imp_txt2@example.com", "SecurePass1!")
    h = auth_headers(tokens)

    resp = await _upload(client, h, "titled.txt", b"The Title Line\n\nBody here.", "text/plain")
    assert resp.status_code == 201

    # Verify the created note's title via the notes endpoint
    note_id = resp.json()["note_id"]
    note_resp = await client.get(f"/api/v1/notes/{note_id}", headers=h)
    assert note_resp.status_code == 200
    assert note_resp.json()["title"] == "The Title Line"


# ---------------------------------------------------------------------------
# md (markdown)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_import_md_success(client: AsyncClient):
    tokens = await register_and_login(client, "imp_md@example.com", "SecurePass1!")
    h = auth_headers(tokens)

    content = b"# Markdown Heading\n\nSome **bold** text."
    resp = await _upload(client, h, "readme.md", content, "text/markdown")

    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "success"
    assert body["uploaded_file"]["extension"] == "md"


@pytest.mark.asyncio
async def test_import_md_strips_heading_marker(client: AsyncClient):
    tokens = await register_and_login(client, "imp_md2@example.com", "SecurePass1!")
    h = auth_headers(tokens)

    resp = await _upload(client, h, "doc.md", b"# Clean Title\n\nContent.", "text/markdown")
    note_id = resp.json()["note_id"]
    note = await client.get(f"/api/v1/notes/{note_id}", headers=auth_headers(tokens))
    assert note.json()["title"] == "Clean Title"


# ---------------------------------------------------------------------------
# csv
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_import_csv_success(client: AsyncClient):
    tokens = await register_and_login(client, "imp_csv@example.com", "SecurePass1!")
    h = auth_headers(tokens)

    csv_data = b"name,age,city\nAlice,30,London\nBob,25,Paris\nCarol,28,Tokyo"
    resp = await _upload(client, h, "people.csv", csv_data, "text/csv")

    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "success"
    assert body["uploaded_file"]["extension"] == "csv"


@pytest.mark.asyncio
async def test_import_csv_note_content_has_table(client: AsyncClient):
    tokens = await register_and_login(client, "imp_csv2@example.com", "SecurePass1!")
    h = auth_headers(tokens)

    csv_data = b"product,price\nApple,1.20\nBanana,0.50"
    resp = await _upload(client, h, "products.csv", csv_data, "text/csv")
    note_id = resp.json()["note_id"]

    note = await client.get(f"/api/v1/notes/{note_id}", headers=h)
    content = note.json()["content"]
    assert "product" in content
    assert "Apple" in content
    assert "|" in content        # table formatting
    assert "2 row" in content    # summary line


@pytest.mark.asyncio
async def test_import_csv_title_has_row_count(client: AsyncClient):
    tokens = await register_and_login(client, "imp_csv3@example.com", "SecurePass1!")
    h = auth_headers(tokens)

    csv_data = b"a,b\n1,2\n3,4\n5,6"
    resp = await _upload(client, h, "nums.csv", csv_data, "text/csv")
    note_id = resp.json()["note_id"]
    note = await client.get(f"/api/v1/notes/{note_id}", headers=h)
    assert "3" in note.json()["title"]  # 3 data rows


@pytest.mark.asyncio
async def test_import_empty_csv(client: AsyncClient):
    tokens = await register_and_login(client, "imp_csv4@example.com", "SecurePass1!")
    h = auth_headers(tokens)

    resp = await _upload(client, h, "empty.csv", b"", "text/csv")
    # Empty CSV should still succeed — the converter handles it gracefully
    assert resp.status_code == 201
    assert resp.json()["status"] == "success"


# ---------------------------------------------------------------------------
# json
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_import_json_object_success(client: AsyncClient):
    tokens = await register_and_login(client, "imp_json@example.com", "SecurePass1!")
    h = auth_headers(tokens)

    payload = json.dumps({"title": "Config", "version": 2, "active": True}).encode()
    resp = await _upload(client, h, "config.json", payload, "application/json")

    assert resp.status_code == 201
    assert resp.json()["status"] == "success"
    assert resp.json()["uploaded_file"]["extension"] == "json"


@pytest.mark.asyncio
async def test_import_json_content_is_pretty_printed(client: AsyncClient):
    tokens = await register_and_login(client, "imp_json2@example.com", "SecurePass1!")
    h = auth_headers(tokens)

    data = {"x": 1, "y": [1, 2, 3]}
    resp = await _upload(client, h, "data.json", json.dumps(data).encode(), "application/json")
    note_id = resp.json()["note_id"]

    note = await client.get(f"/api/v1/notes/{note_id}", headers=h)
    content = note.json()["content"]
    # Pretty-printed → must contain newlines and indentation
    assert "\n" in content
    parsed_back = json.loads(content)
    assert parsed_back == data


@pytest.mark.asyncio
async def test_import_json_array_success(client: AsyncClient):
    tokens = await register_and_login(client, "imp_json3@example.com", "SecurePass1!")
    h = auth_headers(tokens)

    payload = json.dumps([{"id": 1}, {"id": 2}, {"id": 3}]).encode()
    resp = await _upload(client, h, "items.json", payload, "application/json")
    assert resp.status_code == 201
    assert "3 items" in resp.json()["import_record"]["note_id"] or resp.json()["status"] == "success"


@pytest.mark.asyncio
async def test_import_invalid_json_graceful_fallback(client: AsyncClient):
    tokens = await register_and_login(client, "imp_json4@example.com", "SecurePass1!")
    h = auth_headers(tokens)

    resp = await _upload(client, h, "bad.json", b"{not valid json!!}", "application/json")
    # Should succeed — converter falls back to raw text instead of crashing
    assert resp.status_code == 201
    assert resp.json()["status"] == "success"
    note_id = resp.json()["note_id"]
    note = await client.get(f"/api/v1/notes/{note_id}", headers=h)
    assert "invalid" in note.json()["title"].lower()


# ---------------------------------------------------------------------------
# Rejection cases
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_import_pdf_rejected(client: AsyncClient):
    tokens = await register_and_login(client, "imp_pdf@example.com", "SecurePass1!")
    h = auth_headers(tokens)

    resp = await _upload(client, h, "document.pdf", b"%PDF-1.4 fake", "application/pdf")
    assert resp.status_code == 400
    assert "pdf" in resp.json()["detail"].lower() or "unsupported" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_import_png_rejected(client: AsyncClient):
    tokens = await register_and_login(client, "imp_png@example.com", "SecurePass1!")
    h = auth_headers(tokens)

    resp = await _upload(client, h, "photo.png", b"\x89PNG fake image", "image/png")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_import_py_rejected(client: AsyncClient):
    tokens = await register_and_login(client, "imp_py@example.com", "SecurePass1!")
    h = auth_headers(tokens)

    resp = await _upload(client, h, "script.py", b"print('hello')", "text/x-python")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_import_requires_auth(client: AsyncClient):
    resp = await client.post(
        "/api/v1/imports/upload",
        files={"file": ("test.txt", io.BytesIO(b"hello"), "text/plain")},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_import_oversized_file_rejected(client: AsyncClient):
    tokens = await register_and_login(client, "imp_big@example.com", "SecurePass1!")
    h = auth_headers(tokens)

    # 6 MB > 5 MB limit
    big_content = b"x" * (6 * 1024 * 1024)
    resp = await _upload(client, h, "big.txt", big_content, "text/plain")
    assert resp.status_code == 413


# ---------------------------------------------------------------------------
# Import history
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_import_history_recorded(client: AsyncClient):
    tokens = await register_and_login(client, "imp_hist@example.com", "SecurePass1!")
    h = auth_headers(tokens)

    await _upload(client, h, "first.txt", b"First file", "text/plain")
    await _upload(client, h, "second.md", b"# Second\nContent", "text/markdown")

    resp = await client.get("/api/v1/imports/history", headers=h)
    assert resp.status_code == 200
    history = resp.json()
    assert len(history) == 2
    statuses = {r["status"] for r in history}
    assert statuses == {"success"}


@pytest.mark.asyncio
async def test_import_history_has_note_id(client: AsyncClient):
    tokens = await register_and_login(client, "imp_hist2@example.com", "SecurePass1!")
    h = auth_headers(tokens)

    upload_resp = await _upload(client, h, "linked.txt", b"Some content", "text/plain")
    expected_note_id = upload_resp.json()["note_id"]

    history_resp = await client.get("/api/v1/imports/history", headers=h)
    record = history_resp.json()[0]
    assert record["note_id"] == expected_note_id


@pytest.mark.asyncio
async def test_import_history_scoped_to_user(client: AsyncClient):
    tokens_a = await register_and_login(client, "imp_scope_a@example.com", "SecurePass1!")
    tokens_b = await register_and_login(client, "imp_scope_b@example.com", "SecurePass1!")

    await _upload(client, auth_headers(tokens_a), "a.txt", b"User A file", "text/plain")
    await _upload(client, auth_headers(tokens_a), "b.txt", b"Also A", "text/plain")

    resp = await client.get("/api/v1/imports/history", headers=auth_headers(tokens_b))
    assert resp.json() == []


@pytest.mark.asyncio
async def test_import_history_requires_auth(client: AsyncClient):
    resp = await client.get("/api/v1/imports/history")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_import_history_pagination(client: AsyncClient):
    tokens = await register_and_login(client, "imp_page@example.com", "SecurePass1!")
    h = auth_headers(tokens)

    for i in range(5):
        await _upload(client, h, f"file{i}.txt", f"Content {i}".encode(), "text/plain")

    resp = await client.get("/api/v1/imports/history?limit=2&offset=0", headers=h)
    assert len(resp.json()) == 2

    resp2 = await client.get("/api/v1/imports/history?limit=2&offset=4", headers=h)
    assert len(resp2.json()) == 1


# ---------------------------------------------------------------------------
# Note ownership from import
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_imported_note_owned_by_importer(client: AsyncClient):
    tokens = await register_and_login(client, "imp_own@example.com", "SecurePass1!")
    h = auth_headers(tokens)

    resp = await _upload(client, h, "mine.txt", b"My content", "text/plain")
    note_id = resp.json()["note_id"]

    # The owner can access it
    note_resp = await client.get(f"/api/v1/notes/{note_id}", headers=h)
    assert note_resp.status_code == 200

    # Another user cannot
    tokens_b = await register_and_login(client, "imp_own_b@example.com", "SecurePass1!")
    other_resp = await client.get(f"/api/v1/notes/{note_id}", headers=auth_headers(tokens_b))
    assert other_resp.status_code == 404
