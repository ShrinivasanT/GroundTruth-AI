"""Refetch Agent — LangGraph node factory.

Monitors retrieval quality.  When the maximum relevance score falls below
a configurable threshold (default ``0.65``), the agent:

1. Uses the LLM (``gpt-5-nano``) to reformulate the user question into an
   optimised arXiv search query.
2. Fetches 1–2 new papers via the existing ArxivClient.
3. Runs a micro-ingestion through the IngestionPipeline using the active
   ``session_id``.
4. Increments ``refetch_count`` so the conditional edge can route back to the
   retriever node for a second pass.

This entire process is **transparent** — the user is never prompted.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from langchain_openai import ChatOpenAI

from app.agents.state import AgentState
from app.models.api import IngestPapersRequest
from app.models.domain import PaperSource

if TYPE_CHECKING:
    from app.core.config import Settings
    from app.ingestion.pipeline import IngestionPipeline
    from app.services.arxiv_client import ArxivClient

logger = logging.getLogger(__name__)

_REFORMULATE_PROMPT = (
    "You are a scientific search query optimizer. Given the user's question, "
    "produce a concise, keyword-rich arXiv search query (max 12 words) that "
    "will retrieve the most relevant papers. Return ONLY the query string, "
    "no explanation."
)


def make_refetch_node(
    settings: Settings,
    arxiv_client: ArxivClient,
    ingestion_pipeline: IngestionPipeline,
):
    """Return an async LangGraph node that micro-ingests papers on low relevance.

    Parameters
    ----------
    settings:
        Application settings (provides API key, model, threshold, paper limit).
    arxiv_client:
        Live ArxivClient for searching additional papers.
    ingestion_pipeline:
        The existing IngestionPipeline to download, parse, embed, and index.
    """

    llm = ChatOpenAI(
        model=settings.openai_agent_model,
        api_key=settings.openai_api_key,
        temperature=0.0,
    )

    async def refetch(state: AgentState) -> dict:
        query: str = state["query"]
        session_id: str | None = state.get("session_id")
        refetch_count: int = state.get("refetch_count", 0)

        logger.info(
            "RefetchAgent: triggered (refetch_count=%d). Reformulating query for arXiv.",
            refetch_count,
        )

        # Step 1 — LLM reformulates the question into an arXiv query.
        response = await llm.ainvoke(
            [
                {"role": "system", "content": _REFORMULATE_PROMPT},
                {"role": "user", "content": query},
            ]
        )
        arxiv_query = response.content.strip().strip('"').strip("'")
        logger.info("RefetchAgent: reformulated query → %r", arxiv_query)

        # Step 2 — search arXiv for new papers.
        paper_limit = settings.refetch_paper_limit
        new_papers = await arxiv_client.search(arxiv_query, limit=paper_limit)
        if not new_papers:
            logger.warning("RefetchAgent: arXiv returned no papers for %r", arxiv_query)
            return {"refetch_count": refetch_count + 1}

        logger.info(
            "RefetchAgent: arXiv returned %d papers. Starting micro-ingestion.",
            len(new_papers),
        )

        # Step 3 — micro-ingest each paper into the active session.
        request = IngestPapersRequest(
            query=arxiv_query,
            sources=[PaperSource.ARXIV],
            limit=paper_limit,
        )
        await ingestion_pipeline.ingest(request, session_id=session_id)

        return {"refetch_count": refetch_count + 1}

    return refetch
