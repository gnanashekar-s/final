# tests/test_main.py
"""
API tests for the root endpoint.
"""
import pytest
from httpx import AsyncClient
from fastapi import status
from main import app

@pytest.mark.asyncio
async def test_read_root():
    """
    Test that GET '/' returns status 200 and body 'helo world' as plain text.
    """
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/")
    assert response.status_code == status.HTTP_200_OK
    assert response.text == "helo world"
    assert response.headers["content-type"].startswith("text/plain")

@pytest.mark.asyncio
async def test_method_not_allowed():
    """
    Test that POST '/' returns 405 Method Not Allowed.
    """
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/")
    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

@pytest.mark.asyncio
async def test_not_found():
    """
    Test that GET '/foo' returns 404 Not Found.
    """
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/foo")
    assert response.status_code == status.HTTP_404_NOT_FOUND
