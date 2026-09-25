"""Session management service — tracks active learning sessions.

Provides topic-to-category classification (LLM with keyword fallback) and
an in-memory session store used by the chat router endpoints.
"""

from __future__ import annotations

import logging
import re
import threading
import time
import uuid
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Topic → category classification
# ---------------------------------------------------------------------------

# Keyword buckets used as a fast fallback when the LLM is unavailable.
_CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "ai": [
        "ai", "artificial intelligence", "machine learning", "deep learning",
        "neural network", "nlp", "natural language", "computer vision",
        "reinforcement learning", "transformer", "llm", "large language",
        "generative", "diffusion", "gan", "convolutional", "recurrent",
        "classification", "object detection", "robotics", "autonomous",
        "embedding", "fine-tun", "pre-train", "gpt", "bert",
    ],
    "healthcare": [
        "health", "medical", "clinical", "biomedical", "genomic",
        "drug", "pharma", "patient", "diagnosis", "disease",
        "pathology", "radiology", "surgical", "oncology", "epidemi",
        "neuroscience", "brain", "cardio", "therapy", "treatment",
    ],
    "social": [
        "social", "society", "political", "economic", "psychology",
        "sociology", "cultural", "demographic", "education", "policy",
        "public opinion", "media", "communication", "ethics", "bias",
        "inequality", "gender", "race", "community", "urban",
    ],
    "law": [
        "law", "legal", "regulation", "compliance", "court",
        "statute", "legislation", "constitutional", "privacy",
        "intellectual property", "patent", "copyright", "contract",
        "criminal", "jurisdiction", "judicial", "governance",
    ],
}

_LLM_CLASSIFICATION_PROMPT = """\
You are a topic classifier. Given the user's learning topic, classify it into
exactly ONE of these categories: ai, healthcare, social, law, general.

Rules:
- Respond with ONLY the single lowercase category word.
- If the topic clearly belongs to one of the first four categories, choose it.
- If it spans multiple categories or does not fit any, respond with "general".

Topic: {topic}
"""


def classify_topic_keyword(topic: str) -> str:
    """Classify a topic string using keyword matching (no LLM required)."""
    normalised = topic.strip().lower()
    scores: dict[str, int] = {cat: 0 for cat in _CATEGORY_KEYWORDS}
    for cat, keywords in _CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in normalised:
                scores[cat] += 1
    best = max(scores, key=scores.get)  # type: ignore[arg-type]
    if scores[best] > 0:
        return best
    return "general"


async def classify_topic_llm(topic: str, *, api_key: str, model: str) -> str:
    """Classify a topic using an OpenAI chat model.

    Falls back to keyword classification on any error.
    """
    try:
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(model=model, api_key=api_key, temperature=0.0)
        response = await llm.ainvoke(
            [
                {"role": "system", "content": "You classify topics into categories."},
                {"role": "user", "content": _LLM_CLASSIFICATION_PROMPT.format(topic=topic)},
            ]
        )
        raw = response.content.strip().lower()
        # Sanitise: the model should return a single word.
        match = re.search(r"\b(ai|healthcare|social|law|general)\b", raw)
        if match:
            return match.group(1)
        logger.warning("LLM returned unexpected category %r — falling back to keywords.", raw)
    except Exception:
        logger.exception("LLM topic classification failed — falling back to keywords.")
    return classify_topic_keyword(topic)


# ---------------------------------------------------------------------------
# Session model
# ---------------------------------------------------------------------------


class SessionModel(BaseModel):
    """Represents a single active learning session."""

    session_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:16])
    topic: str
    category: str = "general"
    paper_results: list[dict[str, Any]] = Field(default_factory=list)
    ingestion_status: str = "completed"
    last_activity: float = Field(default_factory=time.time)


# ---------------------------------------------------------------------------
# In-memory session store
# ---------------------------------------------------------------------------


class SessionService:
    """Thread-safe, in-memory session manager.

    Parameters
    ----------
    openai_api_key:
        If set, LLM-based classification is used. Otherwise keyword fallback.
    openai_model:
        The OpenAI model used for classification (defaults to gpt-5-nano).
    """

    def __init__(
        self,
        *,
        openai_api_key: str | None = None,
        openai_model: str = "gpt-5-nano",
    ) -> None:
        self._sessions: dict[str, SessionModel] = {}
        self._lock = threading.Lock()
        self._openai_api_key = openai_api_key
        self._openai_model = openai_model

    # -- classification ----------------------------------------------------

    async def classify(self, topic: str) -> str:
        """Return the canonical category for *topic*."""
        if self._openai_api_key:
            return await classify_topic_llm(
                topic,
                api_key=self._openai_api_key,
                model=self._openai_model,
            )
        return classify_topic_keyword(topic)

    # -- CRUD --------------------------------------------------------------

    def create(self, topic: str, category: str) -> SessionModel:
        session = SessionModel(topic=topic, category=category)
        with self._lock:
            self._sessions[session.session_id] = session
        logger.info(
            "SessionService: created session %s  topic=%r  category=%s",
            session.session_id,
            topic,
            category,
        )
        return session

    def get(self, session_id: str) -> SessionModel | None:
        with self._lock:
            session = self._sessions.get(session_id)
            if session:
                session.last_activity = time.time()
            return session

    def delete(self, session_id: str) -> SessionModel | None:
        with self._lock:
            return self._sessions.pop(session_id, None)

    def list_sessions(self) -> list[SessionModel]:
        with self._lock:
            return list(self._sessions.values())
