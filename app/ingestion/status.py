from dataclasses import dataclass, field

from app.models.api import IngestedPaperResult
from app.models.domain import IngestionJobStatus


@dataclass
class IngestionJob:
    job_id: str
    status: IngestionJobStatus
    papers: list[IngestedPaperResult] = field(default_factory=list)
    error: str | None = None


class IngestionStatusStore:
    def __init__(self) -> None:
        self._jobs: dict[str, IngestionJob] = {}

    def create(self, job_id: str) -> IngestionJob:
        job = IngestionJob(job_id=job_id, status=IngestionJobStatus.PENDING)
        self._jobs[job_id] = job
        return job

    def get(self, job_id: str) -> IngestionJob | None:
        return self._jobs.get(job_id)
