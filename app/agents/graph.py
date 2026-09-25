"""LangGraph StateGraph — builds and compiles the FactChat agent pipeline.

The compiled graph is the single entry-point for every user query.

Default path (no ``@agent`` tag)::

    route_input → retrieve → (refetch if low scores, then retry retrieve)
                → repo_enrich → recommend → synthesize_answer

Callable agent branches (Phase 4 placeholders)::

    route_input → buddy_placeholder / review_placeholder / writer_placeholder
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from langgraph.graph import END, StateGraph

from app.agents.retriever_agent import make_retrieve_node
from app.agents.repo_agent import make_repo_enrich_node
from app.agents.refetch_agent import make_refetch_node
from app.agents.recommendation_agent import make_recommend_node
from app.agents.synthesizer import make_synthesize_node
from app.agents.callable_agents import make_buddy_node, make_review_node, make_writer_node
from app.agents.state import AgentState
from app.core.config import get_settings

if TYPE_CHECKING:
    import httpx

    from app.core.config import Settings
    from app.ingestion.pipeline import IngestionPipeline
    from app.retrieval.service import HybridRetriever
    from app.services.arxiv_client import ArxivClient

logger = logging.getLogger(__name__)

_AGENT_TAG_PATTERN = re.compile(r"@(buddy|review|writer)\b", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Routing functions (used as conditional edges)
# ---------------------------------------------------------------------------


def _route_input(state: AgentState) -> str:
    """Check for an explicit ``@agent`` tag in the query.

    Returns the name of the next node to execute.
    """
    match = _AGENT_TAG_PATTERN.search(state["query"])
    if match:
        tag = match.group(1).lower()
        logger.info("Router: detected @%s tag — branching to callable placeholder.", tag)
        return f"{tag}_placeholder"
    return "retrieve"


def _refetch_decision(state: AgentState) -> str:
    """Decide whether the Refetch Agent should fire.

    Conditions (all must be true for a refetch):
    - Retrieval returned no hits **or** the top score is below the threshold.
    - ``refetch_count`` is 0 (only one refetch cycle per query).
    - A ``session_id`` is present (refetching into global collections is not
      supported yet).
    """
    scores = state.get("relevance_scores", [])
    refetch_count = state.get("refetch_count", 0)
    session_id = state.get("session_id")

    # Use module-level get_settings (patchable by tests).
    threshold = get_settings().refetch_relevance_threshold

    if session_id and refetch_count == 0:
        if not scores or max(scores) < threshold:
            logger.info(
                "RefetchDecision: triggering refetch (max_score=%.4f, threshold=%.2f)",
                max(scores) if scores else 0.0,
                threshold,
            )
            return "refetch"

    return "repo_enrich"


# Specialty agents are loaded from app.agents.callable_agents


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------


def build_graph(
    *,
    settings: Settings,
    retriever: HybridRetriever,
    http_client: httpx.AsyncClient,
    arxiv_client: ArxivClient,
    ingestion_pipeline: IngestionPipeline,
) -> StateGraph:
    """Construct and compile the FactChat LangGraph.

    All heavy dependencies are injected here so the node closures can
    capture them without relying on global state.

    Parameters
    ----------
    settings:
        Application settings (API keys, model names, thresholds).
    retriever:
        Wired ``HybridRetriever`` for vector search.
    http_client:
        Shared ``httpx.AsyncClient`` for Repo Agent GitHub API calls.
    arxiv_client:
        ``ArxivClient`` for Refetch Agent paper discovery.
    ingestion_pipeline:
        ``IngestionPipeline`` for Refetch Agent micro-ingestion.

    Returns
    -------
    A compiled LangGraph ready for ``await graph.ainvoke(state)``.
    """

    # ── Create node functions from factories ────────────────────────────
    retrieve_node = make_retrieve_node(retriever)
    repo_enrich_node = make_repo_enrich_node(http_client)
    refetch_node = make_refetch_node(settings, arxiv_client, ingestion_pipeline)
    recommend_node = make_recommend_node(settings)
    synthesize_node = make_synthesize_node(settings)
    buddy_node = make_buddy_node(settings, retriever)
    review_node = make_review_node(settings, retriever)
    writer_node = make_writer_node(settings, retriever)

    # ── Assemble the graph ──────────────────────────────────────────────
    builder = StateGraph(AgentState)

    # Core nodes
    builder.add_node("retrieve", retrieve_node)
    builder.add_node("refetch", refetch_node)
    builder.add_node("repo_enrich", repo_enrich_node)
    builder.add_node("recommend", recommend_node)
    builder.add_node("synthesize_answer", synthesize_node)

    # Callable specialty agents
    builder.add_node("buddy_placeholder", buddy_node)
    builder.add_node("review_placeholder", review_node)
    builder.add_node("writer_placeholder", writer_node)

    # ── Edges ───────────────────────────────────────────────────────────

    # Entry: route based on @agent tags.
    builder.set_conditional_entry_point(
        _route_input,
        {
            "retrieve": "retrieve",
            "buddy_placeholder": "buddy_placeholder",
            "review_placeholder": "review_placeholder",
            "writer_placeholder": "writer_placeholder",
        },
    )

    # After retrieval: decide whether to refetch or continue.
    builder.add_conditional_edges(
        "retrieve",
        _refetch_decision,
        {
            "refetch": "refetch",
            "repo_enrich": "repo_enrich",
        },
    )

    # Refetch loops back to retrieve for a second pass.
    builder.add_edge("refetch", "retrieve")

    # Default pipeline continuation.
    builder.add_edge("repo_enrich", "recommend")
    builder.add_edge("recommend", "synthesize_answer")
    builder.add_edge("synthesize_answer", END)

    # Callable placeholders terminate immediately.
    builder.add_edge("buddy_placeholder", END)
    builder.add_edge("review_placeholder", END)
    builder.add_edge("writer_placeholder", END)

    return builder.compile()
