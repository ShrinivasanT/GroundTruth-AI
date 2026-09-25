import asyncio
import logging
from datetime import datetime

import httpx

from app.core.config import Settings
from app.models.domain import PaperMetadata, PaperSource
from app.utils.ids import build_paper_id, build_title_hash

logger = logging.getLogger(__name__)


class HuggingFaceClient:
    """Search papers via the public HuggingFace Daily Papers API."""

    def __init__(self, http_client: httpx.AsyncClient, settings: Settings) -> None:
        self._client = http_client
        self._settings = settings

    async def search(self, query: str, limit: int) -> list[PaperMetadata]:
        """Search HuggingFace papers and return metadata with arXiv PDF URLs."""
        params = {"q": query}
        max_retries = 3
        backoff = 3.0

        for attempt in range(max_retries):
            try:
                response = await self._client.get(
                    str(self._settings.huggingface_papers_api_url),
                    params=params,
                )
                if response.status_code == 429:
                    if attempt < max_retries - 1:
                        logger.warning(
                            "HuggingFaceClient: Rate limited (429). Retrying in %.1fs (attempt %d/%d)...",
                            backoff, attempt + 1, max_retries,
                        )
                        await asyncio.sleep(backoff)
                        backoff *= 2.0
                        continue
                response.raise_for_status()
                results = response.json()
                return self._parse_results(results, limit)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 429 and attempt < max_retries - 1:
                    logger.warning("HuggingFaceClient: Rate limited (429). Retrying in %.1fs...", backoff)
                    await asyncio.sleep(backoff)
                    backoff *= 2.0
                    continue
                raise
            except (httpx.RequestError, asyncio.TimeoutError) as exc:
                if attempt < max_retries - 1:
                    logger.warning(
                        "HuggingFaceClient: Request failed (%s). Retrying in %.1fs...", exc, backoff,
                    )
                    await asyncio.sleep(backoff)
                    backoff *= 2.0
                    continue
                raise
        return []

    def _parse_results(self, results: list[dict], limit: int) -> list[PaperMetadata]:
        """Convert HuggingFace JSON results into PaperMetadata objects."""
        papers: list[PaperMetadata] = []
        for item in results[:limit]:
            mapped = self._item_to_metadata(item)
            if mapped:
                papers.append(mapped)
        return papers

    def _item_to_metadata(self, item: dict) -> PaperMetadata | None:
        """Map a single HuggingFace paper entry to PaperMetadata."""
        paper_data = item.get("paper")
        if not paper_data:
            return None

        arxiv_id = paper_data.get("id")
        title = paper_data.get("title")
        if not arxiv_id or not title:
            return None

        clean_title = " ".join(title.split())
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}"

        # Parse authors — HuggingFace nests author names inside objects.
        raw_authors = paper_data.get("authors", [])
        authors = [a.get("name", "") for a in raw_authors if a.get("name")]

        # Parse published date.
        published_date = None
        published_text = paper_data.get("publishedAt")
        if published_text:
            try:
                published_date = datetime.fromisoformat(published_text.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                pass

        # Use AI-generated keywords as categories when available.
        categories = paper_data.get("ai_keywords", [])

        abstract = paper_data.get("summary", "")

        return PaperMetadata(
            paper_id=build_paper_id(arxiv_id=arxiv_id, doi=None, title=clean_title),
            source=PaperSource.ARXIV,
            title=clean_title,
            authors=authors,
            abstract=abstract,
            published_date=published_date,
            categories=categories,
            pdf_url=pdf_url,
            arxiv_id=arxiv_id,
            doi=None,
            title_hash=build_title_hash(clean_title),
        )
