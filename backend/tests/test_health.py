"""Basic smoke tests for the app as a whole."""

import pytest


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "simulate" in body


@pytest.mark.asyncio
async def test_openapi_schema(client):
    resp = await client.get("/openapi.json")
    assert resp.status_code == 200
    schema = resp.json()
    assert "paths" in schema
    # All three route groups must appear
    paths = schema["paths"]
    assert any("/api/sensors" in p for p in paths)
    assert any("/api/readings" in p for p in paths)
    assert any("/api/alert-rules" in p for p in paths)
