import asyncio
import logging
import xml.etree.ElementTree as ET
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)

from app.core.config import Settings
from app.models.domain import PaperMetadata, PaperSource
from app.utils.ids import build_paper_id, build_title_hash

ATOM_NS = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}


class ArxivClient:
    def __init__(self, http_client: httpx.AsyncClient, settings: Settings) -> None:
        self._client = http_client
        self._settings = settings

    async def search(self, query: str, limit: int) -> list[PaperMetadata]:
        params = {
            "search_query": f"all:{query}",
            "start": 0,
            "max_results": limit,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
        max_retries = 3
        backoff = 3.0
        for attempt in range(max_retries):
            try:
                response = await self._client.get(str(self._settings.arxiv_base_url), params=params)
                if response.status_code == 429:
                    if attempt < max_retries - 1:
                        logger.warning("ArxivClient: Rate limited (429). Retrying in %.1fs (attempt %d/%d)...", backoff, attempt + 1, max_retries)
                        await asyncio.sleep(backoff)
                        backoff *= 2.0
                        continue
                response.raise_for_status()
                return self._parse_feed(response.text)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 429 and attempt < max_retries - 1:
                    logger.warning("ArxivClient: Rate limited (429). Retrying in %.1fs...", backoff)
                    await asyncio.sleep(backoff)
                    backoff *= 2.0
                    continue
                raise
            except (httpx.RequestError, asyncio.TimeoutError) as exc:
                if attempt < max_retries - 1:
                    logger.warning("ArxivClient: Request failed (%s). Retrying in %.1fs...", exc, backoff)
                    await asyncio.sleep(backoff)
                    backoff *= 2.0
                    continue
                raise
        return []

    async def latest(self, limit: int, category: str | None = None) -> list[PaperMetadata]:
        params = {
            "search_query": f"cat:{category}" if category else "all:*",
            "start": 0,
            "max_results": limit,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
        max_retries = 3
        backoff = 3.0
        for attempt in range(max_retries):
            try:
                response = await self._client.get(str(self._settings.arxiv_base_url), params=params)
                if response.status_code == 429:
                    if attempt < max_retries - 1:
                        logger.warning("ArxivClient: Rate limited (429). Retrying in %.1fs (attempt %d/%d)...", backoff, attempt + 1, max_retries)
                        await asyncio.sleep(backoff)
                        backoff *= 2.0
                        continue
                response.raise_for_status()
                return self._parse_feed(response.text)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 429 and attempt < max_retries - 1:
                    logger.warning("ArxivClient: Rate limited (429). Retrying in %.1fs...", backoff)
                    await asyncio.sleep(backoff)
                    backoff *= 2.0
                    continue
                raise
            except (httpx.RequestError, asyncio.TimeoutError) as exc:
                if attempt < max_retries - 1:
                    logger.warning("ArxivClient: Request failed (%s). Retrying in %.1fs...", exc, backoff)
                    await asyncio.sleep(backoff)
                    backoff *= 2.0
                    continue
                raise
        return []

    def _parse_feed(self, payload: str) -> list[PaperMetadata]:
        root = ET.fromstring(payload)
        results: list[PaperMetadata] = []
        for entry in root.findall("atom:entry", ATOM_NS):
            mapped = self._entry_to_metadata(entry)
            if mapped:
                results.append(mapped)
        return results

    def _entry_to_metadata(self, entry: ET.Element) -> PaperMetadata | None:
        entry_id = self._get_text(entry, "atom:id")
        title = self._get_text(entry, "atom:title")
        if not entry_id or not title:
            return None
        arxiv_id = entry_id.rsplit("/", maxsplit=1)[-1]
        pdf_url = next(
            (
                link.attrib.get("href")
                for link in entry.findall("atom:link", ATOM_NS)
                if link.attrib.get("title") == "pdf" or link.attrib.get("type") == "application/pdf"
            ),
            f"https://arxiv.org/pdf/{arxiv_id}.pdf",
        )
        published_text = self._get_text(entry, "atom:published")
        published_date = None
        if published_text:
            published_date = datetime.fromisoformat(published_text.replace("Z", "+00:00"))
        authors = [
            author.findtext("atom:name", default="", namespaces=ATOM_NS).strip()
            for author in entry.findall("atom:author", ATOM_NS)
        ]
        categories = [category.attrib.get("term", "") for category in entry.findall("atom:category", ATOM_NS)]
        doi = self._find_doi(entry)
        clean_title = " ".join(title.split())
        return PaperMetadata(
            paper_id=build_paper_id(arxiv_id=arxiv_id, doi=doi, title=clean_title),
            source=PaperSource.ARXIV,
            title=clean_title,
            authors=[author for author in authors if author],
            abstract=self._get_text(entry, "atom:summary") or "",
            published_date=published_date,
            categories=[category for category in categories if category],
            pdf_url=pdf_url,
            arxiv_id=arxiv_id,
            doi=doi,
            title_hash=build_title_hash(clean_title),
        )

    @staticmethod
    def _get_text(entry: ET.Element, path: str) -> str | None:
        value = entry.findtext(path, default="", namespaces=ATOM_NS).strip()
        return value or None

    @staticmethod
    def _find_doi(entry: ET.Element) -> str | None:
        for identifier in entry.findall("arxiv:doi", ATOM_NS):
            if identifier.text:
                return identifier.text.strip()
        return None
