import re
from collections.abc import Iterable


_NON_WORD_RE = re.compile(r"[^a-z0-9]+")


def normalize_title(title: str) -> str:
    normalized = title.strip().lower()
    normalized = _NON_WORD_RE.sub(" ", normalized)
    return " ".join(normalized.split())


def truncate_text(value: str, limit: int) -> str:
    value = value.strip()
    if len(value) <= limit:
        return value
    return f"{value[: limit - 3].rstrip()}..."


def compact_whitespace(value: str) -> str:
    return " ".join(value.split())


def join_non_empty(parts: Iterable[str]) -> str:
    return "\n\n".join(part.strip() for part in parts if part and part.strip())
