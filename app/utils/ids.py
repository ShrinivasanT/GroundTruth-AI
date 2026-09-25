import hashlib

from app.models.domain import PaperMetadata
from app.utils.text import normalize_title


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def build_title_hash(title: str) -> str:
    return sha256_hex(normalize_title(title))


def build_paper_id(arxiv_id: str | None, doi: str | None, title: str) -> str:
    if arxiv_id:
        normalized = arxiv_id.strip().lower().replace("/", "_")
        return f"paper:arxiv:{normalized}"
    if doi:
        normalized = doi.strip().lower().replace("/", "_")
        return f"paper:doi:{normalized}"
    return f"paper:title:{build_title_hash(title)}"


def build_record_id(prefix: str, paper_id: str, unique_text: str) -> str:
    return f"{prefix}:{paper_id}:{sha256_hex(unique_text)[:24]}"


def attach_identity_fields(metadata: PaperMetadata) -> PaperMetadata:
    data = metadata.model_dump()
    data["title_hash"] = build_title_hash(metadata.title)
    data["paper_id"] = build_paper_id(metadata.arxiv_id, metadata.doi, metadata.title)
    return PaperMetadata(**data)
