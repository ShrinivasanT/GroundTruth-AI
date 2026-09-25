import logging
from collections.abc import Sequence

from app.llm.groq_service import GroqSemanticService
from app.models.domain import PaperMetadata, PaperSource
from app.services.arxiv_client import ArxivClient
from app.services.huggingface_client import HuggingFaceClient

logger = logging.getLogger(__name__)

# Queries with 3 words or fewer are already concise enough — skip LLM extraction.
_MAX_SHORT_QUERY_WORDS = 3


class PaperDiscoveryService:
    def __init__(
        self,
        arxiv_client: ArxivClient,
        huggingface_client: HuggingFaceClient,
        groq_service: GroqSemanticService,
    ) -> None:
        self._arxiv_client = arxiv_client
        self._huggingface_client = huggingface_client
        self._groq_service = groq_service

    async def search(self, query: str, sources: Sequence[PaperSource], limit: int) -> list[PaperMetadata]:
        """Discover papers using Groq topic extraction → HuggingFace search.

        When the query is short (≤ 3 words) it is used as-is.  For longer
        queries the Groq LLM distils the query into a concise search topic
        before hitting the HuggingFace papers API.
        """
        search_query = await self._maybe_extract_topic(query)
        logger.info("PaperDiscoveryService: query=%r → search_query=%r", query, search_query)
        papers = await self._huggingface_client.search(query=search_query, limit=limit)
        return self._deduplicate(papers)[:limit]

    async def latest(self, sources: Sequence[PaperSource], limit: int, category: str | None = None) -> list[PaperMetadata]:
        papers = await self._arxiv_client.latest(limit=limit, category=category)
        return self._deduplicate(papers)[:limit]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _maybe_extract_topic(self, query: str) -> str:
        """Run Groq topic extraction only when the query has > 3 words."""
        if len(query.split()) <= _MAX_SHORT_QUERY_WORDS:
            return query
        return await self._groq_service.extract_search_topic(query)

    @staticmethod
    def _deduplicate(papers: list[PaperMetadata]) -> list[PaperMetadata]:
        seen_by_id: dict[str, PaperMetadata] = {}
        seen_identity: dict[str, str] = {}
        ordered: list[PaperMetadata] = []
        for paper in papers:
            keys = [paper.paper_id, paper.title_hash]
            if paper.arxiv_id:
                keys.append(f"arxiv:{paper.arxiv_id.lower()}")
            if paper.doi:
                keys.append(f"doi:{paper.doi.lower()}")
            canonical_id = next((seen_identity[key] for key in keys if key in seen_identity), None)
            if canonical_id:
                existing = seen_by_id[canonical_id]
                seen_by_id[canonical_id] = PaperMetadata(
                    **{
                        **existing.model_dump(),
                        **{k: v for k, v in paper.model_dump().items() if v not in (None, "", [], {})},
                    }
                )
                continue
            seen_by_id[paper.paper_id] = paper
            for key in keys:
                seen_identity[key] = paper.paper_id
            ordered.append(paper)
        return [seen_by_id[paper.paper_id] for paper in ordered]
