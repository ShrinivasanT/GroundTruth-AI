import asyncio

from app.embeddings.fastembed_service import FastEmbedService
from app.models.domain import RetrievalHit, RetrievalSource
from app.utils.text import compact_whitespace, truncate_text
from app.vectorstores.milvus_store import MilvusStore


class HybridRetriever:
    def __init__(self, embeddings: FastEmbedService, store: MilvusStore) -> None:
        self._embeddings = embeddings
        self._store = store

    async def retrieve(
        self,
        question: str,
        top_k: int,
        *,
        session_id: str | None = None,
        category: str | None = None,
    ) -> list[RetrievalHit]:
        query_variants = self._expand_query(question)
        query_embeddings = await self._embeddings.embed_texts(query_variants)
        merged: dict[str, RetrievalHit] = {}
        for embedding in query_embeddings:
            chunk_hits, table_hits, figure_hits = await asyncio.gather(
                self._store.search_chunks(embedding, top_k, session_id=session_id, category=category),
                self._store.search_tables(embedding, top_k, session_id=session_id, category=category),
                self._store.search_figures(embedding, top_k, session_id=session_id, category=category),
            )
            self._merge_hits(merged, chunk_hits, RetrievalSource.CHUNK)
            self._merge_hits(merged, table_hits, RetrievalSource.TABLE)
            self._merge_hits(merged, figure_hits, RetrievalSource.FIGURE)
        ranked = sorted(merged.values(), key=lambda item: item.score, reverse=True)
        for index, hit in enumerate(ranked[:top_k], start=1):
            hit.citation_label = f"C{index}"
        return ranked[:top_k]

    def _merge_hits(self, bucket: dict[str, RetrievalHit], hits: list[dict], source: RetrievalSource) -> None:
        for rank, hit in enumerate(hits, start=1):
            parsed = self._to_hit(hit, source=source, rank=rank)
            existing = bucket.get(parsed.source_id)
            if existing is None or parsed.score > existing.score:
                bucket[parsed.source_id] = parsed

    def _to_hit(self, hit: dict, source: RetrievalSource, rank: int) -> RetrievalHit:
        score = float(hit.get("score", 0.0)) + (1.0 / (rank + 5))
        if source is RetrievalSource.CHUNK:
            return RetrievalHit(
                source=source,
                source_id=hit["chunk_id"],
                paper_id=hit["paper_id"],
                title=hit["title"],
                content=truncate_text(compact_whitespace(hit["text"]), 1800),
                section=hit.get("section"),
                page=hit.get("page"),
                score=score,
                citation_label="",
            )
        if source is RetrievalSource.TABLE:
            return RetrievalHit(
                source=source,
                source_id=hit["table_id"],
                paper_id=hit["paper_id"],
                title="Table result",
                content=truncate_text(compact_whitespace(hit.get("table_summary") or hit.get("table_markdown") or ""), 1800),
                section="table",
                page=hit.get("page"),
                score=score,
                citation_label="",
            )
        return RetrievalHit(
            source=source,
            source_id=hit["figure_id"],
            paper_id=hit["paper_id"],
            title="Figure result",
            content=truncate_text(compact_whitespace(hit.get("figure_description") or hit.get("figure_caption") or ""), 1800),
            section="figure",
            page=hit.get("page"),
            score=score,
            citation_label="",
        )

    @staticmethod
    def _expand_query(question: str) -> list[str]:
        base = compact_whitespace(question)
        lowered = base.lower()
        return [base, f"scientific evidence for {lowered}", f"{lowered} methods results limitations"]
