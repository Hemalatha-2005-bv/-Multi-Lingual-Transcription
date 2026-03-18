from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job
from app.repositories.interfaces import IJobRepository


class JobRepository(IJobRepository):
    """SQLite-backed job repository using SQLAlchemy async."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, job_id: str, title: str) -> Job:
        job = Job(id=job_id, status="pending", title=title)
        self._session.add(job)
        await self._session.commit()
        await self._session.refresh(job)
        return job

    async def get(self, job_id: str) -> Optional[Job]:
        result = await self._session.execute(select(Job).where(Job.id == job_id))
        return result.scalar_one_or_none()

    async def update_status(self, job_id: str, status: str) -> None:
        job = await self.get(job_id)
        if job:
            job.status = status
            job.updated_at = datetime.now(timezone.utc)
            await self._session.commit()

    async def complete(
        self,
        job_id: str,
        results: list[dict],
        txt: str,
        srt: str,
    ) -> None:
        job = await self.get(job_id)
        if job:
            job.status = "completed"
            job.set_results(results)
            job.txt = txt
            job.srt = srt
            job.updated_at = datetime.now(timezone.utc)
            await self._session.commit()

    async def fail(self, job_id: str, error: str) -> None:
        job = await self.get(job_id)
        if job:
            job.status = "error"
            job.error = error
            job.updated_at = datetime.now(timezone.utc)
            await self._session.commit()
