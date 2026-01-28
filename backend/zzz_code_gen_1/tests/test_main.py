# tests/test_main.py
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

# --- Book CRUD tests ---
def test_create_and_get_book():
    # Create a book
    payload = {
        "id": 1,
        "title": "Test Book",
        "author": "Author",
        "year": 2023,
        "availability": True
    }
    r = client.post("/books/", json=payload)
    assert r.status_code == 201
    data = r.json()
    assert data["id"] == 1
    assert data["title"] == "Test Book"
    assert data["author"] == "Author"
    assert data["year"] == 2023
    assert data["availability"] is True

    # Get the book
    r2 = client.get("/books/1")
    assert r2.status_code == 200
    data2 = r2.json()
    assert data2["id"] == 1
    assert data2["title"] == "Test Book"


def test_duplicate_book_id():
    payload = {
        "id": 2,
        "title": "Book2",
        "author": "Author2",
        "year": 2022,
        "availability": False
    }
    r1 = client.post("/books/", json=payload)
    assert r1.status_code == 201
    r2 = client.post("/books/", json=payload)
    assert r2.status_code == 400
    assert r2.json()["detail"] == "Book with this ID already exists."


def test_missing_required_fields():
    payload = {
        "id": 3,
        "title": "Book3",
        # Missing author, year, availability
    }
    r = client.post("/books/", json=payload)
    assert r.status_code == 422


def test_invalid_field_types():
    payload = {
        "id": "not-an-int",
        "title": 123,
        "author": True,
        "year": "not-a-year",
        "availability": "not-a-bool"
    }
    r = client.post("/books/", json=payload)
    assert r.status_code == 422


def test_get_nonexistent_book():
    r = client.get("/books/9999")
    assert r.status_code == 404
    assert r.json()["detail"] == "Book not found"


def test_update_book():
    payload = {
        "id": 10,
        "title": "Old Title",
        "author": "Old Author",
        "year": 2000,
        "availability": True
    }
    client.post("/books/", json=payload)
    update_payload = {
        "id": 10,
        "title": "New Title",
        "author": "New Author",
        "year": 2021,
        "availability": False
    }
    r = client.put("/books/10", json=update_payload)
    assert r.status_code == 200
    data = r.json()
    assert data["title"] == "New Title"
    assert data["author"] == "New Author"
    assert data["year"] == 2021
    assert data["availability"] is False


def test_patch_book_partial_update():
    payload = {
        "id": 20,
        "title": "Patch Title",
        "author": "Patch Author",
        "year": 2010,
        "availability": True
    }
    client.post("/books/", json=payload)
    patch_payload = {"title": "Patched Title"}
    r = client.patch("/books/20", json=patch_payload)
    assert r.status_code == 200
    data = r.json()
    assert data["title"] == "Patched Title"
    assert data["author"] == "Patch Author"


def test_delete_book():
    payload = {
        "id": 30,
        "title": "Delete Me",
        "author": "Author",
        "year": 2015,
        "availability": True
    }
    client.post("/books/", json=payload)
    r = client.delete("/books/30")
    assert r.status_code == 204
    r2 = client.get("/books/30")
    assert r2.status_code == 404


def test_delete_nonexistent_book():
    r = client.delete("/books/99999")
    assert r.status_code == 404
    assert r.json()["detail"] == "Book not found"


def test_sensitive_endpoints_forbidden_in_production(monkeypatch):
    monkeypatch.setenv("ENV", "production")
    r = client.get("/cleanup")
    assert r.status_code == 403
    r = client.get("/reset")
    assert r.status_code == 403


def test_sensitive_endpoints_allowed_in_development(monkeypatch):
    monkeypatch.setenv("ENV", "development")
    r = client.get("/cleanup")
    assert r.status_code == 200
    assert r.json()["message"] == "Cleanup completed."
    r = client.get("/reset")
    assert r.status_code == 200
    assert r.json()["message"] == "Reset completed."
