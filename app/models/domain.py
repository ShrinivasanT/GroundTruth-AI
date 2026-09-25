from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class PaperSource(str, Enum):
    ARXIV = "arxiv"


# ---------------------------------------------------------------------------
# The five canonical topic categories for global collection routing.
# ---------------------------------------------------------------------------
TOPIC_CATEGORIES: list[str] = ["ai", "healthcare", "social", "law", "general"]


class PaperMetadata(BaseModel):
    paper_id: str
    source: PaperSource
    title: str
    authors: list[str] = Field(default_factory=list)
    abstract: str = ""
    published_date: datetime | None = None
    categories: list[str] = Field(default_factory=list)
    pdf_url: str
    arxiv_id: str | None = None
    doi: str | None = None
    title_hash: str


class ChunkRecord(BaseModel):
    chunk_id: str
    paper_id: str
    title: str
    section: str
    text: str
    page: int | None = None
    references: list[str] = Field(default_factory=list)
    embedding: list[float] = Field(default_factory=list)


class TableRecord(BaseModel):
    table_id: str
    paper_id: str
    page: int | None = None
    table_markdown: str
    table_summary: str
    embedding: list[float] = Field(default_factory=list)


class FigureRecord(BaseModel):
    figure_id: str
    paper_id: str
    page: int | None = None
    figure_caption: str
    figure_description: str
    image_path: str
    embedding: list[float] = Field(default_factory=list)


class ParsedPaper(BaseModel):
    metadata: PaperMetadata
    local_pdf_path: Path
    parsed_json_path: Path
    structured_document: dict[str, Any]
    chunks: list[ChunkRecord]
    tables: list[TableRecord]
    figures: list[FigureRecord]


class RetrievalSource(str, Enum):
    CHUNK = "chunk"
    TABLE = "table"
    FIGURE = "figure"


class RetrievalHit(BaseModel):
    source: RetrievalSource
    source_id: str
    paper_id: str
    title: str
    content: str
    section: str | None = None
    page: int | None = None
    score: float
    citation_label: str


class IngestionJobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
