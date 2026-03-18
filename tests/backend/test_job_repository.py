"""Tests for JobRepository CRUD operations."""

import uuid
import pytest


@pytest.mark.asyncio
async def test_create_and_get_job(job_repo):
    job_id = str(uuid.uuid4())
    job = await job_repo.create(job_id, "test_video.mp4")
    assert job.id == job_id
    assert job.status == "pending"
    assert job.title == "test_video.mp4"

    fetched = await job_repo.get(job_id)
    assert fetched is not None
    assert fetched.id == job_id


@pytest.mark.asyncio
async def test_get_nonexistent_returns_none(job_repo):
    result = await job_repo.get("nonexistent-id")
    assert result is None


@pytest.mark.asyncio
async def test_update_status(job_repo):
    job_id = str(uuid.uuid4())
    await job_repo.create(job_id, "video.mp4")
    await job_repo.update_status(job_id, "transcribing")
    job = await job_repo.get(job_id)
    assert job.status == "transcribing"


@pytest.mark.asyncio
async def test_complete_job(job_repo):
    job_id = str(uuid.uuid4())
    await job_repo.create(job_id, "video.mp4")

    results = [{"transcript": "Hello", "confidence": -0.2, "language_code": "en", "words": []}]
    await job_repo.complete(job_id, results, "Hello\n", "1\n00:00:00,000 --> ...\nHello\n")

    job = await job_repo.get(job_id)
    assert job.status == "completed"
    assert job.get_results() == results
    assert job.txt == "Hello\n"


@pytest.mark.asyncio
async def test_fail_job(job_repo):
    job_id = str(uuid.uuid4())
    await job_repo.create(job_id, "video.mp4")
    await job_repo.fail(job_id, "FFmpeg not found.")

    job = await job_repo.get(job_id)
    assert job.status == "error"
    assert job.error == "FFmpeg not found."
