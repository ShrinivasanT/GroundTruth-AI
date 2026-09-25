"""Word Document (.docx) Generator — Programmatically compiles Markdown to Word."""

from __future__ import annotations

import os
import re
import logging
from docx import Document

logger = logging.getLogger(__name__)


def generate_docx_from_markdown(markdown_text: str, output_path: str) -> None:
    """Parse basic Markdown layout and compile a styled Word document.

    Supports headers (H1, H2, H3), bullet points, and clean paragraphs.

    Parameters
    ----------
    markdown_text : str
        The raw Markdown text synthesized by the Writer Agent.
    output_path : str
        Target file path where the .docx file will be saved.
    """
    logger.info("DocxGenerator: starting compilation to %s", output_path)

    # Ensure parent directories exist
    parent_dir = os.path.dirname(output_path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)

    doc = Document()

    # Split document by lines
    lines = markdown_text.splitlines()

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Skip separator blocks (e.g. "---", "### 🔬 Sandbox Verification Log")
        # and ignore the Word export summary block if it's already there
        if stripped == "---" or "🔬 Sandbox Verification" in stripped or "📄 Programmatic Word Export" in stripped:
            continue

        # Headers
        if stripped.startswith("# "):
            header_text = re.sub(r"\*\*([^*]+)\*\*", r"\1", stripped[2:])
            doc.add_heading(header_text, level=1)
        elif stripped.startswith("## "):
            header_text = re.sub(r"\*\*([^*]+)\*\*", r"\1", stripped[3:])
            doc.add_heading(header_text, level=2)
        elif stripped.startswith("### "):
            header_text = re.sub(r"\*\*([^*]+)\*\*", r"\1", stripped[4:])
            doc.add_heading(header_text, level=3)
        # Bullet list items
        elif stripped.startswith("- ") or stripped.startswith("* "):
            # Strip markdown bold highlights from lists
            clean_text = re.sub(r"\*\*([^*]+)\*\*", r"\1", stripped[2:])
            doc.add_paragraph(clean_text, style="List Bullet")
        # Regular paragraphs
        else:
            # Strip markdown bold highlights from text
            clean_text = re.sub(r"\*\*([^*]+)\*\*", r"\1", stripped)
            doc.add_paragraph(clean_text)

    doc.save(output_path)
    logger.info("DocxGenerator: Word document saved successfully (%d lines)", len(lines))
