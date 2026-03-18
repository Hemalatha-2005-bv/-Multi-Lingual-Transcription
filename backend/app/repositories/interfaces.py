from abc import ABC, abstractmethod
from typing import Optional

from app.models.job import Job


class IJobRepository(ABC):
    """Abstract repository — all storage implementations must satisfy this contract."""

    @abstractmethod
    async def create(self, job_id: str, title: str) -> Job:
        ...

    @abstractmethod
    async def get(self, job_id: str) -> Optional[Job]:
        ...

    @abstractmethod
    async def update_status(self, job_id: str, status: str) -> None:
        ...

    @abstractmethod
    async def complete(
        self,
        job_id: str,
        results: list[dict],
        txt: str,
        srt: str,
    ) -> None:
        ...

    @abstractmethod
    async def fail(self, job_id: str, error: str) -> None:
        ...
