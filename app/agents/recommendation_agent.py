"""Recommendation Agent — LangGraph node factory.

Generates follow-up suggestions and detects topic drift / vagueness by
comparing the current query to the session's initial learning topic.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from langchain_openai import ChatOpenAI

from app.agents.state import AgentState, RecommendationResult

if TYPE_CHECKING:
    from app.core.config import Settings

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are a scientific research assistant that analyses the user's query in the
context of a learning session.

You are given:
- The original session topic (what the user said they wanted to learn).
- The current user query.
- Titles and brief content from the top retrieved citations.

Produce a JSON object (no markdown fences) with these exact keys:
{
  "follow_ups": ["...", "..."],       // 2-3 suggested follow-up questions
  "agent_suggestions": ["..."],       // e.g. "Use @buddy to generate code for this algorithm"
  "drift_detected": false,            // true if query drifts far from session topic
  "new_session_recommended": false,   // true if a new session would serve the user better
  "drift_message": ""                 // human-readable explanation if drift is detected
}
Return ONLY valid JSON.
"""


def make_recommend_node(settings: Settings):
    """Return an async LangGraph node for follow-up recommendation and drift detection.

    Parameters
    ----------
    settings:
        Application settings (provides API key and agent model name).
    """

    llm = ChatOpenAI(
        model=settings.openai_agent_model,
        api_key=settings.openai_api_key,
        temperature=0.3,
    )

    async def recommend(state: AgentState) -> dict:
        query: str = state["query"]
        session_topic: str | None = state.get("session_topic")
        hits = state.get("retrieval_hits", [])

        # Build a compact context summary for the LLM.
        citation_summaries = "\n".join(
            f"- [{h.citation_label}] {h.title}: {h.content[:200]}"
            for h in hits[:5]
        )

        user_content = (
            f"Session topic: {session_topic or 'Not specified'}\n"
            f"Current query: {query}\n\n"
            f"Top retrieved citations:\n{citation_summaries}"
        )

        try:
            response = await llm.ainvoke(
                [
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ]
            )
            raw = response.content.strip()
            # Strip markdown fences if the model wraps them despite instructions.
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            result = RecommendationResult(**json.loads(raw))
        except Exception:
            logger.exception("RecommendationAgent: failed to parse LLM response")
            result = RecommendationResult()

        logger.info(
            "RecommendationAgent: follow_ups=%d  drift=%s  new_session=%s",
            len(result.follow_ups),
            result.drift_detected,
            result.new_session_recommended,
        )

        return {
            "recommendations": result.follow_ups + result.agent_suggestions,
            "drift_warning": result.drift_message if result.drift_detected else None,
        }

    return recommend
