import logging
from pathlib import Path

from groq import AsyncGroq

from app.core.config import Settings
from app.utils.text import truncate_text

logger = logging.getLogger(__name__)


class GroqSemanticService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = AsyncGroq(api_key=settings.groq_api_key) if settings.groq_api_key else None

    async def extract_search_topic(self, query: str) -> str:
        """Distil a verbose user query into a concise search topic for paper discovery.

        Examples the LLM should handle:
            "transformers"               → "attention"
            "how do large language models work" → "large language models"
            "latest research on protein folding" → "protein folding"

        Returns the original *query* unchanged when the Groq client is not
        configured so the pipeline can still function.
        """
        if not self._client:
            return query

        prompt = (
            "You are a research librarian. Given a user's research interest, "
            "return ONLY the core search topic or keyword that would find the "
            "most relevant academic papers. No explanation, no punctuation, no "
            "quotation marks — just the topic phrase.\n\n"
            "Examples:\n"
            "  User: transformers → attention\n"
            "  User: how do large language models work → large language models\n"
            "  User: latest advances in drug discovery using AI → AI drug discovery\n"
            "  User: protein folding prediction → protein folding\n\n"
            f"User: {query}"
        )
        try:
            response = await self._client.chat.completions.create(
                model=self._settings.groq_keyword_model,
                temperature=0.0,
                messages=[
                    {"role": "system", "content": "You extract concise academic search topics."},
                    {"role": "user", "content": prompt},
                ],
            )
            content = response.choices[0].message.content
            return content.strip() if content else query
        except Exception:
            logger.warning("Groq keyword extraction failed; falling back to raw query.")
            return query

    async def describe_table(self, title: str, table_markdown: str) -> str:
        prompt = (
            "Summarize the scientific table for retrieval. Focus on variables, metrics, trends, and main findings. "
            "Return 3-4 compact sentences.\n\n"
            f"Paper title: {title}\n"
            f"Table:\n{truncate_text(table_markdown, 12000)}"
        )
        return await self._complete(prompt, fallback="Table summary unavailable.")

    async def describe_figure(self, title: str, caption: str, image_path: str) -> str:
        prompt = (
            "Produce a retrieval-oriented semantic description of the scientific figure or graph. "
            "Infer likely axes, comparison intent, and takeaway from the caption and paper context. "
            "Avoid hedging unless necessary. Return 3-4 compact sentences.\n\n"
            f"Paper title: {title}\n"
            f"Figure caption: {caption or 'No caption available'}\n"
            f"Stored figure path: {Path(image_path).name}"
        )
        return await self._complete(prompt, fallback=caption or "Figure description unavailable.")

    async def _complete(self, prompt: str, fallback: str) -> str:
        if not self._client:
            return fallback
        response = await self._client.chat.completions.create(
            model=self._settings.groq_model,
            temperature=0.1,
            messages=[
                {"role": "system", "content": "You write concise scientific retrieval metadata."},
                {"role": "user", "content": prompt},
            ],
        )
        content = response.choices[0].message.content
        return content.strip() if content else fallback
