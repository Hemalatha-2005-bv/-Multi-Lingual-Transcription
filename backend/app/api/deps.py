"""FastAPI dependency providers."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.repositories.job_repository import JobRepository
from app.services.transcription_service import TranscriptionService


def get_job_repository(
    session: AsyncSession = Depends(get_session),
) -> JobRepository:
    return JobRepository(session)


def get_transcription_service(
    repo: JobRepository = Depends(get_job_repository),
) -> TranscriptionService:
    return TranscriptionService(repo)
