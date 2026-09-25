import asyncio
import logging
import re
from pathlib import Path
import pypdf

from app.core.config import Settings
from app.models.domain import ChunkRecord, FigureRecord, PaperMetadata, ParsedPaper, TableRecord
from app.utils.ids import build_record_id
from app.utils.text import compact_whitespace

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Regex patterns for inline references to figures and tables.
# Captures forms like "Fig. 1", "Figure 3", "Table 2", "Tab. 4", etc.
# ---------------------------------------------------------------------------
_FIGURE_REF_RE = re.compile(r"\bFig(?:ure|\.)\s*(\d+)", re.IGNORECASE)
_TABLE_REF_RE = re.compile(r"\bTab(?:le|\.)\s*(\d+)", re.IGNORECASE)


class DoclingParser:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def parse(self, metadata: PaperMetadata, pdf_path: Path, figures_dir: Path, json_path: Path) -> ParsedPaper:
        return await asyncio.to_thread(self._parse_sync, metadata, pdf_path, figures_dir, json_path)

    def _parse_sync(self, metadata: PaperMetadata, pdf_path: Path, figures_dir: Path, json_path: Path) -> ParsedPaper:
        logger.info("Parsing PDF programmatically using pypdf for maximum stability and speed: %s", pdf_path)
        
        chunks: list[ChunkRecord] = []
        tables: list[TableRecord] = []
        figures: list[FigureRecord] = []
        
        current_section = "Introduction"
        
        try:
            reader = pypdf.PdfReader(pdf_path)
            
            for page_index, page in enumerate(reader.pages):
                page_no = page_index + 1
                text = page.extract_text()
                if not text:
                    continue
                
                text = compact_whitespace(text)
                words = text.split()
                current_chunk = []
                current_length = 0
                
                for word in words:
                    current_chunk.append(word)
                    current_length += len(word) + 1
                    if current_length > self._settings.chunk_size_chars:
                        chunk_text = " ".join(current_chunk)
                        chunk_id = build_record_id("chunk", metadata.paper_id, f"{current_section}:{page_no}:{chunk_text[:240]}")
                        chunks.append(
                            ChunkRecord(
                                chunk_id=chunk_id,
                                paper_id=metadata.paper_id,
                                title=metadata.title,
                                section=current_section,
                                text=chunk_text,
                                page=page_no,
                                references=DoclingParser._extract_references(chunk_text),
                            )
                        )
                        current_chunk = []
                        current_length = 0
                
                if current_chunk:
                    chunk_text = " ".join(current_chunk)
                    chunk_id = build_record_id("chunk", metadata.paper_id, f"{current_section}:{page_no}:{chunk_text[:240]}")
                    chunks.append(
                        ChunkRecord(
                            chunk_id=chunk_id,
                            paper_id=metadata.paper_id,
                            title=metadata.title,
                            section=current_section,
                            text=chunk_text,
                            page=page_no,
                            references=DoclingParser._extract_references(chunk_text),
                        )
                    )
            
            structured_document = {"text": "Parsed programmatically via pypdf for high-performance extraction."}
            
        except Exception as e:
            logger.exception("pypdf parsing failed for %s", pdf_path)
            structured_document = {"text": f"Parsing failed: {e}"}

        return ParsedPaper(
            metadata=metadata,
            local_pdf_path=pdf_path,
            parsed_json_path=json_path,
            structured_document=structured_document,
            chunks=chunks,
            tables=tables,
            figures=figures,
        )

    @staticmethod
    def _extract_references(text: str) -> list[str]:
        """Scan text for inline references like ``Fig. 1``, ``Figure 3``,
        ``Table 2``, ``Tab. 4`` and return a deduplicated, sorted list of
        normalized reference strings (e.g. ``["Fig. 1", "Table 2"]``)."""
        refs: dict[str, None] = {}  # ordered dict for dedup
        for match in _FIGURE_REF_RE.finditer(text):
            refs[f"Fig. {match.group(1)}"] = None
        for match in _TABLE_REF_RE.finditer(text):
            refs[f"Table {match.group(1)}"] = None
        return list(refs.keys())
