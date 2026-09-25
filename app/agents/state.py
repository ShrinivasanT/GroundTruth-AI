"""Shared state schema and output models for the LangGraph agent pipeline."""

from __future__ import annotations

from typing import Any, TypedDict

from pydantic import BaseModel, Field

from app.models.domain import RetrievalHit


# ---------------------------------------------------------------------------
# LangGraph shared state
# ---------------------------------------------------------------------------


class AgentState(TypedDict, total=False):
    """Typed dictionary flowing through every LangGraph node.

    Keys are optional (``total=False``) so nodes only need to return the
    subset they modify.
    """

    # Request context
    session_id: str | None
    category: str | None
    session_topic: str | None
    query: str
    top_k: int

    # Retrieval outputs
    retrieval_hits: list[RetrievalHit]
    relevance_scores: list[float]
    refetch_count: int

    # Enrichment outputs
    github_repos: list[dict[str, Any]]
    recommendations: list[str]
    drift_warning: str | None

    # Routing
    callable_agent_type: str | None

    # Final output
    final_answer: str


# ---------------------------------------------------------------------------
# Pydantic output models used by individual agents
# ---------------------------------------------------------------------------


class RepoInfo(BaseModel):
    """Metadata for a GitHub repository found in paper content."""

    owner: str
    name: str
    description: str = ""
    stars: int = 0
    language: str = ""
    topics: list[str] = Field(default_factory=list)
    html_url: str


class RecommendationResult(BaseModel):
    """Structured output of the Recommendation Agent."""

    follow_ups: list[str] = Field(default_factory=list)
    agent_suggestions: list[str] = Field(default_factory=list)
    drift_detected: bool = False
    new_session_recommended: bool = False
    drift_message: str = ""
