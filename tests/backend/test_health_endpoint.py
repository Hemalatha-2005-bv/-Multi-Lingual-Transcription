"""Integration test for the health endpoint."""

import pytest


@pytest.mark.asyncio
async def test_health_returns_ok(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["version"] == "2.0.0"
    assert data["mode"] == "local (offline)"


@pytest.mark.asyncio
async def test_status_404_for_unknown_job(client):
    resp = await client.get("/api/transcription-status/nonexistent-job-id")
    assert resp.status_code == 404
