import asyncio
import logging
from typing import Any

from pymilvus import DataType, MilvusClient

from app.core.config import Settings
from app.models.domain import ChunkRecord, FigureRecord, PaperMetadata, TableRecord

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# The five canonical topic categories used for global collection routing.
# Any topic that does not match one of the first four is mapped to "general".
# ---------------------------------------------------------------------------
VALID_CATEGORIES: set[str] = {"ai", "healthcare", "social", "law", "general"}

# Modality suffixes used when constructing dynamic collection names.
_MODALITIES: list[str] = ["chunks", "tables", "figures"]


class MilvusStore:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = MilvusClient(uri=settings.milvus_uri, token=settings.milvus_token)

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    async def initialize(self) -> None:
        await asyncio.to_thread(self._initialize_sync)

    def healthy(self) -> bool:
        try:
            self._client.list_collections()
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Paper metadata (unchanged – lives in the global papers collection)
    # ------------------------------------------------------------------

    async def find_existing_paper(self, metadata: PaperMetadata) -> dict[str, Any] | None:
        return await asyncio.to_thread(self._find_existing_paper_sync, metadata)

    async def upsert_paper(self, metadata: PaperMetadata) -> None:
        await asyncio.to_thread(
            self._client.upsert,
            collection_name=self._settings.milvus_papers_collection,
            data={
                "paper_id": metadata.paper_id,
                "arxiv_id": metadata.arxiv_id or "",
                "doi": metadata.doi or "",
                "title": metadata.title,
                "authors": metadata.authors,
                "abstract": metadata.abstract,
                "published_date": metadata.published_date.isoformat() if metadata.published_date else "",
                "categories": metadata.categories,
                "pdf_url": metadata.pdf_url,
                "title_hash": metadata.title_hash,
                "embedding": self._zero_embedding(),
            },
        )

    # ------------------------------------------------------------------
    # Upsert helpers – session-aware
    # ------------------------------------------------------------------

    async def upsert_chunks(
        self,
        records: list[ChunkRecord],
        *,
        session_id: str | None = None,
    ) -> None:
        if not records:
            return
        collection = self._resolve_collection_name("chunks", session_id=session_id)
        await asyncio.to_thread(self._ensure_chunks_collection, collection)
        await asyncio.to_thread(
            self._client.upsert,
            collection_name=collection,
            data=[record.model_dump() for record in records],
        )

    async def upsert_tables(
        self,
        records: list[TableRecord],
        *,
        session_id: str | None = None,
    ) -> None:
        if not records:
            return
        collection = self._resolve_collection_name("tables", session_id=session_id)
        await asyncio.to_thread(self._ensure_tables_collection, collection)
        await asyncio.to_thread(
            self._client.upsert,
            collection_name=collection,
            data=[record.model_dump() for record in records],
        )

    async def upsert_figures(
        self,
        records: list[FigureRecord],
        *,
        session_id: str | None = None,
    ) -> None:
        if not records:
            return
        collection = self._resolve_collection_name("figures", session_id=session_id)
        await asyncio.to_thread(self._ensure_figures_collection, collection)
        await asyncio.to_thread(
            self._client.upsert,
            collection_name=collection,
            data=[record.model_dump() for record in records],
        )

    # ------------------------------------------------------------------
    # Search helpers – session / category aware
    # ------------------------------------------------------------------

    async def search_chunks(
        self,
        embedding: list[float],
        limit: int,
        *,
        session_id: str | None = None,
        category: str | None = None,
    ) -> list[dict[str, Any]]:
        collection = self._resolve_collection_name(
            "chunks", session_id=session_id, category=category,
        )
        if not await asyncio.to_thread(self._client.has_collection, collection_name=collection):
            return []
        return await asyncio.to_thread(
            self._search_sync,
            collection,
            embedding,
            limit,
            ["chunk_id", "paper_id", "title", "section", "text", "page"],
        )

    async def search_tables(
        self,
        embedding: list[float],
        limit: int,
        *,
        session_id: str | None = None,
        category: str | None = None,
    ) -> list[dict[str, Any]]:
        collection = self._resolve_collection_name(
            "tables", session_id=session_id, category=category,
        )
        if not await asyncio.to_thread(self._client.has_collection, collection_name=collection):
            return []
        return await asyncio.to_thread(
            self._search_sync,
            collection,
            embedding,
            limit,
            ["table_id", "paper_id", "table_markdown", "table_summary", "page"],
        )

    async def search_figures(
        self,
        embedding: list[float],
        limit: int,
        *,
        session_id: str | None = None,
        category: str | None = None,
    ) -> list[dict[str, Any]]:
        collection = self._resolve_collection_name(
            "figures", session_id=session_id, category=category,
        )
        if not await asyncio.to_thread(self._client.has_collection, collection_name=collection):
            return []
        return await asyncio.to_thread(
            self._search_sync,
            collection,
            embedding,
            limit,
            ["figure_id", "paper_id", "figure_caption", "figure_description", "page"],
        )

    # ------------------------------------------------------------------
    # Session lifecycle – merge & drop
    # ------------------------------------------------------------------

    async def merge_session_to_global(self, session_id: str, category: str) -> None:
        """Copy all vectors from session collections into the corresponding
        global category collections, then drop the session collections."""
        cat = self._normalize_category(category)
        await asyncio.to_thread(self._merge_session_sync, session_id, cat)

    async def drop_session_collections(self, session_id: str) -> None:
        """Drop all three session-scoped collections for the given session."""
        await asyncio.to_thread(self._drop_session_sync, session_id)

    # ==================================================================
    # Private helpers
    # ==================================================================

    # ------------------------------------------------------------------
    # Collection name resolution
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_category(category: str) -> str:
        """Lowercase and clamp to the five valid categories."""
        normalised = category.strip().lower()
        return normalised if normalised in VALID_CATEGORIES else "general"

    def _resolve_collection_name(
        self,
        modality: str,
        *,
        session_id: str | None = None,
        category: str | None = None,
    ) -> str:
        """Determine the target collection name based on context.

        Priority: session_id > category > default (settings-based).
        """
        # If session_id is provided, check if this is a global Xavier Files session (topic is 'AI', 'Healthcare', or 'Social')
        if session_id:
            try:
                from app.api.dependencies import get_session_service
                session_service = get_session_service()
                session = session_service.get(session_id)
                if session and session.topic.lower() in {"ai", "healthcare", "social"}:
                    category = session.category
                    session_id = None
            except Exception:
                pass

        if session_id:
            return f"sess_{session_id}_{modality}"
        if category:
            cat = self._normalize_category(category)
            if cat == "ai":
                return f"Artificial_intellegince_global_{modality}"
            return f"global_{cat}_{modality}"
        # Fall back to the static collection names from settings.
        return {
            "chunks": self._settings.milvus_chunks_collection,
            "tables": self._settings.milvus_tables_collection,
            "figures": self._settings.milvus_figures_collection,
        }[modality]

    # ------------------------------------------------------------------
    # Default initialisation (static global collections)
    # ------------------------------------------------------------------

    def _initialize_sync(self) -> None:
        self._ensure_papers_collection()
        self._ensure_chunks_collection(self._settings.milvus_chunks_collection)
        self._ensure_tables_collection(self._settings.milvus_tables_collection)
        self._ensure_figures_collection(self._settings.milvus_figures_collection)

        # Pre-initialize global collections for all valid categories to be ready immediately
        for cat in VALID_CATEGORIES:
            for modality in _MODALITIES:
                col_name = self._resolve_collection_name(modality, category=cat)
                if modality == "chunks":
                    self._ensure_chunks_collection(col_name)
                elif modality == "tables":
                    self._ensure_tables_collection(col_name)
                elif modality == "figures":
                    self._ensure_figures_collection(col_name)

    # ------------------------------------------------------------------
    # Dynamic collection provisioning
    # ------------------------------------------------------------------

    def _ensure_chunks_collection(self, name: str) -> None:
        """Create the chunks vector collection if it does not exist."""
        self._ensure_vector_collection(
            name=name,
            primary_key="chunk_id",
            fields=[
                ("paper_id", DataType.VARCHAR, {"max_length": 256}),
                ("title", DataType.VARCHAR, {"max_length": 2048}),
                ("section", DataType.VARCHAR, {"max_length": 512}),
                ("text", DataType.VARCHAR, {"max_length": 65535}),
                ("page", DataType.INT64, {}),
                ("references", DataType.JSON, {}),
            ],
        )

    def _ensure_tables_collection(self, name: str) -> None:
        """Create the tables vector collection if it does not exist."""
        self._ensure_vector_collection(
            name=name,
            primary_key="table_id",
            fields=[
                ("paper_id", DataType.VARCHAR, {"max_length": 256}),
                ("page", DataType.INT64, {}),
                ("table_markdown", DataType.VARCHAR, {"max_length": 65535}),
                ("table_summary", DataType.VARCHAR, {"max_length": 65535}),
            ],
        )

    def _ensure_figures_collection(self, name: str) -> None:
        """Create the figures vector collection if it does not exist."""
        self._ensure_vector_collection(
            name=name,
            primary_key="figure_id",
            fields=[
                ("paper_id", DataType.VARCHAR, {"max_length": 256}),
                ("page", DataType.INT64, {}),
                ("figure_caption", DataType.VARCHAR, {"max_length": 8192}),
                ("figure_description", DataType.VARCHAR, {"max_length": 65535}),
                ("image_path", DataType.VARCHAR, {"max_length": 4096}),
            ],
        )

    # ------------------------------------------------------------------
    # Papers collection (unchanged)
    # ------------------------------------------------------------------

    def _ensure_papers_collection(self) -> None:
        name = self._settings.milvus_papers_collection
        if not self._client.has_collection(collection_name=name):
            schema = MilvusClient.create_schema(auto_id=False, enable_dynamic_field=False)
            schema.add_field(field_name="paper_id", datatype=DataType.VARCHAR, is_primary=True, max_length=256)
            schema.add_field(field_name="arxiv_id", datatype=DataType.VARCHAR, max_length=256)
            schema.add_field(field_name="doi", datatype=DataType.VARCHAR, max_length=512)
            schema.add_field(field_name="title", datatype=DataType.VARCHAR, max_length=4096)
            schema.add_field(field_name="authors", datatype=DataType.JSON)
            schema.add_field(field_name="abstract", datatype=DataType.VARCHAR, max_length=65535)
            schema.add_field(field_name="published_date", datatype=DataType.VARCHAR, max_length=128)
            schema.add_field(field_name="categories", datatype=DataType.JSON)
            schema.add_field(field_name="pdf_url", datatype=DataType.VARCHAR, max_length=4096)
            schema.add_field(field_name="title_hash", datatype=DataType.VARCHAR, max_length=64)
            schema.add_field(field_name="embedding", datatype=DataType.FLOAT_VECTOR, dim=self._settings.embedding_dimension)
            self._client.create_collection(collection_name=name, schema=schema)
            index_params = self._client.prepare_index_params()
            index_params.add_index(
                field_name="embedding",
                index_type="HNSW",
                metric_type="COSINE",
                params={"M": 16, "efConstruction": 200},
            )
            self._client.create_index(collection_name=name, index_params=index_params)
        self._client.load_collection(collection_name=name)

    # ------------------------------------------------------------------
    # Generic vector collection creator (shared logic)
    # ------------------------------------------------------------------

    def _ensure_vector_collection(
        self,
        name: str,
        primary_key: str,
        fields: list[tuple[str, DataType, dict[str, Any]]],
    ) -> None:
        if not self._client.has_collection(collection_name=name):
            schema = MilvusClient.create_schema(auto_id=False, enable_dynamic_field=False)
            schema.add_field(field_name=primary_key, datatype=DataType.VARCHAR, is_primary=True, max_length=256)
            for field_name, data_type, kwargs in fields:
                schema.add_field(field_name=field_name, datatype=data_type, **kwargs)
            schema.add_field(field_name="embedding", datatype=DataType.FLOAT_VECTOR, dim=self._settings.embedding_dimension)
            self._client.create_collection(collection_name=name, schema=schema)
            index_params = self._client.prepare_index_params()
            index_params.add_index(
                field_name="embedding",
                index_type="HNSW",
                metric_type="COSINE",
                params={"M": 16, "efConstruction": 200},
            )
            self._client.create_index(collection_name=name, index_params=index_params)
        self._client.load_collection(collection_name=name)

    # ------------------------------------------------------------------
    # Merge session → global (synchronous, run via asyncio.to_thread)
    # ------------------------------------------------------------------

    def _merge_session_sync(self, session_id: str, category: str) -> None:
        """Transfer all records from session collections into the matching
        global category collections."""
        modality_config: dict[str, dict[str, Any]] = {
            "chunks": {
                "primary_key": "chunk_id",
                "output_fields": ["chunk_id", "paper_id", "title", "section", "text", "page", "embedding"],
                "ensure_fn": self._ensure_chunks_collection,
            },
            "tables": {
                "primary_key": "table_id",
                "output_fields": ["table_id", "paper_id", "page", "table_markdown", "table_summary", "embedding"],
                "ensure_fn": self._ensure_tables_collection,
            },
            "figures": {
                "primary_key": "figure_id",
                "output_fields": ["figure_id", "paper_id", "page", "figure_caption", "figure_description", "image_path", "embedding"],
                "ensure_fn": self._ensure_figures_collection,
            },
        }

        for modality, cfg in modality_config.items():
            src = f"sess_{session_id}_{modality}"
            dst = self._resolve_collection_name(modality, category=category)

            if not self._client.has_collection(collection_name=src):
                logger.info("Session collection %s does not exist — skipping merge.", src)
                continue

            # Ensure destination global collection exists.
            cfg["ensure_fn"](dst)

            # Query ALL records from the session collection.
            self._client.load_collection(collection_name=src)
            records = self._client.query(
                collection_name=src,
                filter="",
                output_fields=cfg["output_fields"],
                limit=16384,
            )

            if not records:
                logger.info("Session collection %s is empty — nothing to merge.", src)
                continue

            self._client.upsert(collection_name=dst, data=records)
            logger.info(
                "Merged %d records from %s → %s.",
                len(records),
                src,
                dst,
            )

    # ------------------------------------------------------------------
    # Drop session collections (synchronous, run via asyncio.to_thread)
    # ------------------------------------------------------------------

    def _drop_session_sync(self, session_id: str) -> None:
        for modality in _MODALITIES:
            name = f"sess_{session_id}_{modality}"
            if self._client.has_collection(collection_name=name):
                self._client.drop_collection(collection_name=name)
                logger.info("Dropped session collection %s.", name)

    # ------------------------------------------------------------------
    # Search (unchanged logic)
    # ------------------------------------------------------------------

    def _find_existing_paper_sync(self, metadata: PaperMetadata) -> dict[str, Any] | None:
        self._client.load_collection(collection_name=self._settings.milvus_papers_collection)
        results = self._client.query(
            collection_name=self._settings.milvus_papers_collection,
            filter=self._build_duplicate_filter(metadata),
            output_fields=["paper_id", "arxiv_id", "doi", "title", "title_hash", "pdf_url"],
            limit=1,
        )
        return results[0] if results else None

    def _build_duplicate_filter(self, metadata: PaperMetadata) -> str:
        clauses = [f'paper_id == "{metadata.paper_id}"', f'title_hash == "{metadata.title_hash}"']
        if metadata.arxiv_id:
            clauses.append(f'arxiv_id == "{metadata.arxiv_id}"')
        if metadata.doi:
            clauses.append(f'doi == "{metadata.doi.replace(chr(34), r'\\\"')}"')
        return " or ".join(clauses)

    def _search_sync(self, collection_name: str, embedding: list[float], limit: int, output_fields: list[str]) -> list[dict[str, Any]]:
        self._client.load_collection(collection_name=collection_name)
        results = self._client.search(
            collection_name=collection_name,
            data=[embedding],
            limit=limit,
            output_fields=output_fields,
            search_params={"metric_type": "COSINE", "params": {"ef": 64}},
        )
        hits = results[0] if results else []
        normalized: list[dict[str, Any]] = []
        for hit in hits:
            entity = dict(hit.get("entity") or {})
            entity["score"] = float(hit.get("distance") or hit.get("score") or 0.0)
            normalized.append(entity)
        return normalized

    def _zero_embedding(self) -> list[float]:
        return [0.0] * self._settings.embedding_dimension
