"""Agent Coordinator — FastAPI-facing entry-point for the LangGraph pipeline.

Instantiates the compiled graph once and exposes an ``async query()`` method
that initialises :class:`AgentState` and invokes the graph.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.agents.graph import build_graph
from app.core.config import Settings
from app.ingestion.pipeline import IngestionPipeline
from app.retrieval.service import HybridRetriever
from app.services.arxiv_client import ArxivClient

logger = logging.getLogger(__name__)


class AgentCoordinator:
    """Thread-safe coordinator that holds the compiled LangGraph.

    Parameters
    ----------
    settings:
        Application configuration.
    retriever:
        ``HybridRetriever`` for vector search.
    http_client:
        Shared ``httpx.AsyncClient`` (used by Repo Agent for GitHub API).
    arxiv_client:
        ``ArxivClient`` (used by Refetch Agent for paper discovery).
    ingestion_pipeline:
        ``IngestionPipeline`` (used by Refetch Agent for micro-ingestion).

    Raises
    ------
    RuntimeError
        If ``OPENAI_API_KEY`` is not configured in the settings.
    """

    def __init__(
        self,
        settings: Settings,
        retriever: HybridRetriever,
        http_client: httpx.AsyncClient,
        arxiv_client: ArxivClient,
        ingestion_pipeline: IngestionPipeline,
    ) -> None:
        if not settings.openai_api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not configured. "
                "Please set it in the .env file to enable the agent pipeline."
            )

        self._graph = build_graph(
            settings=settings,
            retriever=retriever,
            http_client=http_client,
            arxiv_client=arxiv_client,
            ingestion_pipeline=ingestion_pipeline,
        )
        logger.info("AgentCoordinator: LangGraph compiled successfully.")

    async def query(
        self,
        query: str,
        top_k: int = 8,
        *,
        session_id: str | None = None,
        category: str | None = None,
        session_topic: str | None = None,
    ) -> dict[str, Any]:
        """Run a user query through the full LangGraph pipeline.

        Returns the final :class:`AgentState` dictionary containing
        ``final_answer``, ``retrieval_hits``, ``github_repos``,
        ``recommendations``, and ``drift_warning``.
        """
        initial_state = {
            "query": query,
            "top_k": top_k,
            "session_id": session_id,
            "category": category,
            "session_topic": session_topic,
            "retrieval_hits": [],
            "relevance_scores": [],
            "refetch_count": 0,
            "github_repos": [],
            "recommendations": [],
            "drift_warning": None,
            "callable_agent_type": None,
            "final_answer": "",
        }

        logger.info(
            "AgentCoordinator: invoking graph for query=%r  session=%s",
            query[:80],
            session_id,
        )

        result = await self._graph.ainvoke(initial_state)
        return result
