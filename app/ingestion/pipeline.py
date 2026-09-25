import asyncio
import logging
import uuid

logger = logging.getLogger(__name__)

from app.embeddings.fastembed_service import FastEmbedService
from app.ingestion.status import IngestionStatusStore
from app.models.api import IngestPapersRequest, IngestedPaperResult
from app.models.domain import IngestionJobStatus, PaperMetadata, ParsedPaper
from app.parsers.docling_parser import DoclingParser
from app.services.paper_service import PaperDiscoveryService
from app.storage.filesystem import FilesystemStorage
from app.utils.text import truncate_text
from app.vectorstores.milvus_store import MilvusStore


class IngestionPipeline:
    def __init__(
        self,
        discovery: PaperDiscoveryService,
        storage: FilesystemStorage,
        parser: DoclingParser,
        embeddings: FastEmbedService,
        milvus: MilvusStore,
        status_store: IngestionStatusStore,
        concurrency: int,
    ) -> None:
        self._discovery = discovery
        self._storage = storage
        self._parser = parser
        self._embeddings = embeddings
        self._milvus = milvus
        self._status_store = status_store
        self._concurrency = concurrency

    async def ingest(self, request: IngestPapersRequest, *, session_id: str | None = None):
        job_id = str(uuid.uuid4())
        job = self._status_store.create(job_id)
        job.status = IngestionJobStatus.RUNNING
        try:
            papers = await self._resolve_papers(request)
            semaphore = asyncio.Semaphore(self._concurrency)
            results = await asyncio.gather(
                *(self._ingest_single(paper, semaphore, session_id=session_id) for paper in papers)
            )
            job.papers = results
            job.status = IngestionJobStatus.COMPLETED
        except Exception as exc:
            job.status = IngestionJobStatus.FAILED
            job.error = str(exc)
            raise
        return job

    async def _resolve_papers(self, request: IngestPapersRequest) -> list[PaperMetadata]:
        if request.latest:
            return await self._discovery.latest(
                sources=request.sources,
                limit=request.limit,
                category=request.category,
            )
        if not request.query:
            raise ValueError("Either query must be provided or latest must be true.")
        return await self._discovery.search(
            query=request.query,
            sources=request.sources,
            limit=request.limit,
        )

    async def _ingest_single(
        self,
        paper: PaperMetadata,
        semaphore: asyncio.Semaphore,
        *,
        session_id: str | None = None,
    ) -> IngestedPaperResult:
        async with semaphore:
            existing = await self._milvus.find_existing_paper(paper)
            if existing:
                await self._milvus.upsert_paper(paper)
                return IngestedPaperResult(
                    paper_id=paper.paper_id,
                    title=paper.title,
                    status="skipped",
                    detail="Paper already indexed; metadata refreshed.",
                )
            try:
                # Download PDF — use temp storage when inside a session.
                if session_id:
                    pdf_path = await self._storage.download_pdf_temp(paper, session_id)
                    paths = await self._storage.ensure_temp_directories(session_id, paper.paper_id)
                else:
                    pdf_path = await self._storage.download_pdf(paper)
                    paths = await self._storage.ensure_paper_directories(paper.paper_id)

                parsed = await self._parser.parse(
                    metadata=paper,
                    pdf_path=pdf_path,
                    figures_dir=paths["figures"],
                    json_path=paths["json"],
                )
                await self._enrich_local(parsed)
                await self._storage.save_parsed_document(paper.paper_id, parsed.structured_document)
                await self._persist(parsed, session_id=session_id)
                return IngestedPaperResult(
                    paper_id=paper.paper_id,
                    title=paper.title,
                    status="ingested",
                    detail="Paper parsed, embedded, and indexed.",
                )
            except BaseException as exc:
                logger.exception("Ingestion failed for paper %s (%s)", paper.title, paper.paper_id)
                return IngestedPaperResult(
                    paper_id=paper.paper_id,
                    title=paper.title,
                    status="failed",
                    detail=str(exc),
                )

    async def _enrich_local(self, parsed: ParsedPaper) -> None:
        """Enrich tables and figures locally without LLM calls.

        - Table summary: first 500 chars of the markdown.
        - Figure description: the caption text extracted by Docling.
        - Embeddings: generated via FastEmbed as before.
        """
        for table in parsed.tables:
            table.table_summary = truncate_text(table.table_markdown, 500)

        for figure in parsed.figures:
            figure.figure_description = figure.figure_caption or "Figure description unavailable."

        chunk_embeddings, table_embeddings, figure_embeddings = await asyncio.gather(
            self._embeddings.embed_texts([chunk.text for chunk in parsed.chunks]),
            self._embeddings.embed_texts([table.table_summary or table.table_markdown for table in parsed.tables]),
            self._embeddings.embed_texts([figure.figure_description or figure.figure_caption for figure in parsed.figures]),
        )
        for chunk, embedding in zip(parsed.chunks, chunk_embeddings, strict=False):
            chunk.embedding = embedding
        for table, embedding in zip(parsed.tables, table_embeddings, strict=False):
            table.embedding = embedding
        for figure, embedding in zip(parsed.figures, figure_embeddings, strict=False):
            figure.embedding = embedding

    async def _persist(self, parsed: ParsedPaper, *, session_id: str | None = None) -> None:
        await self._milvus.upsert_paper(parsed.metadata)
        await asyncio.gather(
            self._milvus.upsert_chunks(parsed.chunks, session_id=session_id),
            self._milvus.upsert_tables(parsed.tables, session_id=session_id),
            self._milvus.upsert_figures(parsed.figures, session_id=session_id),
        )
