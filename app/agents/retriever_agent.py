"""Retriever Agent — LangGraph node factory.

Wraps :class:`HybridRetriever` to populate shared state with ranked
retrieval hits and per-hit relevance scores.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.agents.state import AgentState

if TYPE_CHECKING:
    from app.retrieval.service import HybridRetriever

logger = logging.getLogger(__name__)


def make_retrieve_node(retriever: HybridRetriever):
    """Return an async LangGraph node that performs hybrid retrieval.

    Parameters
    ----------
    retriever:
        A fully-wired :class:`HybridRetriever` instance (FastEmbed + Milvus).
    """

    async def retrieve(state: AgentState) -> dict:
        query: str = state["query"]
        top_k: int = state.get("top_k", 8)
        session_id: str | None = state.get("session_id")
        category: str | None = state.get("category")

        logger.info(
            "RetrieverAgent: query=%r  top_k=%d  session=%s  category=%s",
            query[:80],
            top_k,
            session_id,
            category,
        )

        hits = await retriever.retrieve(
            query,
            top_k,
            session_id=session_id,
            category=category,
        )

        scores = [h.score for h in hits]
        logger.info(
            "RetrieverAgent: returned %d hits  min_score=%.4f  max_score=%.4f",
            len(hits),
            min(scores) if scores else 0.0,
            max(scores) if scores else 0.0,
        )
        return {"retrieval_hits": hits, "relevance_scores": scores}

    return retrieve
