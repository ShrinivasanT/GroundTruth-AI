import asyncio
import json
import shutil
from pathlib import Path

import httpx

from app.core.config import Settings
from app.models.domain import PaperMetadata


class FilesystemStorage:
    def __init__(self, settings: Settings, http_client: httpx.AsyncClient) -> None:
        self._settings = settings
        self._client = http_client

    # ------------------------------------------------------------------
    # Permanent storage (unchanged — used for non-session ingestion)
    # ------------------------------------------------------------------

    async def ensure_paper_directories(self, paper_id: str) -> dict[str, Path]:
        safe_id = paper_id.replace(":", "_")
        base = self._settings.papers_storage_dir / safe_id
        paths = {
            "base": base,
            "pdf": base / "source.pdf",
            "parsed": base / "parsed",
            "figures": base / "figures",
            "json": base / "parsed" / "document.json",
        }
        await asyncio.gather(
            *(asyncio.to_thread(path.mkdir, parents=True, exist_ok=True) for key, path in paths.items() if key in {"base", "parsed", "figures"})
        )
        return paths

    async def download_pdf(self, paper: PaperMetadata) -> Path:
        paths = await self.ensure_paper_directories(paper.paper_id)
        pdf_path = paths["pdf"]
        if pdf_path.exists():
            return pdf_path
        async with self._client.stream("GET", paper.pdf_url, follow_redirects=True) as response:
            response.raise_for_status()
            content = bytearray()
            async for chunk in response.aiter_bytes():
                content.extend(chunk)
        await asyncio.to_thread(pdf_path.write_bytes, bytes(content))
        return pdf_path

    async def save_parsed_document(self, paper_id: str, payload: dict) -> Path:
        paths = await self.ensure_paper_directories(paper_id)
        output = paths["json"]
        serialized = json.dumps(payload, indent=2, ensure_ascii=True)
        await asyncio.to_thread(output.write_text, serialized, "utf-8")
        return output

    # ------------------------------------------------------------------
    # Temporary session storage
    # ------------------------------------------------------------------

    async def ensure_temp_directories(self, session_id: str, paper_id: str) -> dict[str, Path]:
        """Create temporary directories for a session paper download.

        Layout: ``storage/temp/{session_id}/{paper_id}/``
        """
        safe_id = paper_id.replace(":", "_")
        base = self._settings.temp_storage_dir / session_id / safe_id
        paths = {
            "base": base,
            "pdf": base / "source.pdf",
            "parsed": base / "parsed",
            "figures": base / "figures",
            "json": base / "parsed" / "document.json",
        }
        await asyncio.gather(
            *(
                asyncio.to_thread(path.mkdir, parents=True, exist_ok=True)
                for key, path in paths.items()
                if key in {"base", "parsed", "figures"}
            )
        )
        return paths

    async def download_pdf_temp(self, paper: PaperMetadata, session_id: str) -> Path:
        """Download a PDF into the session temp directory."""
        paths = await self.ensure_temp_directories(session_id, paper.paper_id)
        pdf_path = paths["pdf"]
        if pdf_path.exists():
            return pdf_path
        async with self._client.stream("GET", paper.pdf_url, follow_redirects=True) as response:
            response.raise_for_status()
            content = bytearray()
            async for chunk in response.aiter_bytes():
                content.extend(chunk)
        await asyncio.to_thread(pdf_path.write_bytes, bytes(content))
        return pdf_path

    async def cleanup_temp_session(self, session_id: str) -> None:
        """Recursively delete the temp directory for a session."""
        temp_dir = self._settings.temp_storage_dir / session_id
        if temp_dir.exists():
            await asyncio.to_thread(shutil.rmtree, temp_dir, ignore_errors=True)
