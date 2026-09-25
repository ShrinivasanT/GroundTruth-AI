from typing import Literal

from pydantic import BaseModel, Field

from app.models.domain import IngestionJobStatus, PaperMetadata, PaperSource, RetrievalHit


class SearchPapersRequest(BaseModel):
    query: str = Field(min_length=2)
    sources: list[PaperSource] = Field(default_factory=lambda: [PaperSource.ARXIV])
    limit: int = Field(default=10, ge=1, le=50)


class LatestPapersRequest(BaseModel):
    sources: list[PaperSource] = Field(default_factory=lambda: [PaperSource.ARXIV])
    limit: int = Field(default=10, ge=1, le=50)
    category: str | None = None


class PapersResponse(BaseModel):
    papers: list[PaperMetadata]


class IngestPapersRequest(BaseModel):
    query: str | None = None
    latest: bool = False
    sources: list[PaperSource] = Field(default_factory=lambda: [PaperSource.ARXIV])
    limit: int = Field(default=5, ge=1, le=20)
    category: str | None = None


class IngestedPaperResult(BaseModel):
    paper_id: str
    title: str
    status: Literal["ingested", "skipped", "failed"]
    detail: str


class IngestionResponse(BaseModel):
    job_id: str
    status: IngestionJobStatus
    papers: list[IngestedPaperResult]


class IngestionStatusResponse(BaseModel):
    job_id: str
    status: IngestionJobStatus
    papers: list[IngestedPaperResult] = Field(default_factory=list)
    error: str | None = None


class ChatQueryRequest(BaseModel):
    question: str = Field(min_length=1)
    top_k: int = Field(default=8, ge=1, le=20)
    session_id: str | None = None
    category: str | None = None
    session_topic: str | None = None


class ChatQueryResponse(BaseModel):
    answer: str
    citations: list[RetrievalHit]
    repos: list[dict] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    drift_warning: str | None = None


class StartSessionRequest(BaseModel):
    """Body for ``POST /chat/sessions``."""

    topic: str = Field(min_length=2, description="What do you want to learn today?")


class SessionResponse(BaseModel):
    """Response returned when a new session is created."""

    session_id: str
    topic: str
    category: str
    papers: list[IngestedPaperResult]
    ingestion_status: str = "completed"


class EndSessionResponse(BaseModel):
    """Response returned when a session is ended."""

    session_id: str
    category: str
    status: str


class HealthResponse(BaseModel):
    status: str
    milvus: str
