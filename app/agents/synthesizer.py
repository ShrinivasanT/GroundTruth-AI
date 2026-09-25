"""Answer Synthesizer — LangGraph terminal node factory.

Compiles the final RAG-grounded response using **gpt-5-mini** with strict
inline citation formatting (``[C1] (Paper Title, Page X)``).  If the vector
store returned no evidence for the query, the node emits an explicit
"no evidence" disclaimer instead of speculating.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from langchain_openai import ChatOpenAI

from app.agents.state import AgentState

if TYPE_CHECKING:
    from app.core.config import Settings

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are a scientific research assistant. Your task is to synthesize a
comprehensive, well-structured Markdown answer using ONLY the provided
evidence passages.

## Rules
1. Every factual claim MUST include an inline citation in the format:
   [C1] (Paper Title, Page X)
   Use the citation label and metadata from the provided evidence.
2. If no evidence is provided or the evidence does not address the query,
   respond with:
   "I could not find indexed evidence for that question in the active sources."
3. Do NOT speculate or add information beyond what the evidence supports.
4. If GitHub repositories were found in the sources, mention them with
   [Repo] (github.com/owner/repo) tags.
5. Structure the answer with clear headings and bullet points for readability.
"""


def make_synthesize_node(settings: Settings):
    """Return an async LangGraph node that generates the final grounded answer.

    Parameters
    ----------
    settings:
        Application settings (provides API key and chat model name).
    """

    llm = ChatOpenAI(
        model=settings.openai_chat_model,
        api_key=settings.openai_api_key,
        temperature=0.2,
    )

    async def synthesize_answer(state: AgentState) -> dict:
        query: str = state["query"]
        hits = state.get("retrieval_hits", [])
        repos = state.get("github_repos", [])

        if not hits:
            logger.info("Synthesizer: no retrieval hits — returning no-evidence response.")
            return {
                "final_answer": (
                    "I could not find indexed evidence for that question "
                    "in the active sources."
                )
            }

        # Build evidence block.
        evidence_lines: list[str] = []
        for hit in hits:
            page_info = f", Page {hit.page}" if hit.page else ""
            evidence_lines.append(
                f"[{hit.citation_label}] ({hit.title}{page_info}):\n{hit.content}"
            )
        evidence_block = "\n\n".join(evidence_lines)

        # Build repo block if any.
        repo_block = ""
        if repos:
            repo_lines = [
                f"- [Repo] ({r.get('html_url', '')}) — {r.get('description', '')}"
                for r in repos
            ]
            repo_block = "\n\nLinked repositories:\n" + "\n".join(repo_lines)

        user_content = (
            f"User question: {query}\n\n"
            f"Evidence:\n{evidence_block}"
            f"{repo_block}"
        )

        try:
            response = await llm.ainvoke(
                [
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ]
            )
            answer = response.content.strip()
        except Exception:
            logger.exception("Synthesizer: LLM call failed")
            answer = (
                "An error occurred while generating the answer. "
                "Please try again shortly."
            )

        logger.info("Synthesizer: generated answer (%d chars)", len(answer))
        return {"final_answer": answer}

    return synthesize_answer
