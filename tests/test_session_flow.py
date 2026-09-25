"""Integration tests for the full session lifecycle endpoints.

Tests exercise ``POST /chat/sessions``, ``POST /chat/query``, and
``POST /chat/sessions/{session_id}/end`` using heavy mocking so no live
Milvus, arXiv, or OpenAI backend is required.

Run with::

    python -m pytest tests/test_session_flow.py -v
    # or
    python -m unittest tests.test_session_flow -v
"""

from __future__ import annotations

import asyncio
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# ---------------------------------------------------------------------------
# Stub out native-only dependencies so imports resolve without them installed.
# Must happen before any `from app…` import triggers fastembed / pymilvus.
# ---------------------------------------------------------------------------


def _install_stub(name: str, attrs: dict | None = None) -> types.ModuleType:
    """Create and register a fake module in sys.modules if absent."""
    if name in sys.modules:
        return sys.modules[name]
    mod = types.ModuleType(name)
    for attr, val in (attrs or {}).items():
        setattr(mod, attr, val)
    sys.modules[name] = mod
    return mod


# fastembed
_install_stub("fastembed", {"TextEmbedding": MagicMock()})

# pymilvus
_install_stub("pymilvus", {"DataType": MagicMock(), "MilvusClient": MagicMock()})

# docling (full sub-package tree)
_install_stub("docling")
_install_stub("docling.datamodel")
_install_stub("docling.datamodel.base_models", {"InputFormat": MagicMock()})
_install_stub("docling.datamodel.pipeline_options", {"PdfPipelineOptions": MagicMock()})
_install_stub("docling.document_converter", {
    "DocumentConverter": MagicMock(),
    "PdfFormatOption": MagicMock(),
})

# docling_core
_install_stub("docling_core")
_install_stub("docling_core.types")
_install_stub("docling_core.types.doc", {
    "PictureItem": MagicMock(),
    "SectionHeaderItem": MagicMock(),
    "TableItem": MagicMock(),
    "TextItem": MagicMock(),
})

# langgraph
_install_stub("langgraph")
_install_stub("langgraph.graph", {"END": "__end__", "StateGraph": MagicMock()})

# langchain_openai
_install_stub("langchain_openai", {"ChatOpenAI": MagicMock()})


from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fake_settings(**overrides):
    """Return a ``Settings``-like object with safe defaults for testing."""
    from app.core.config import Settings

    defaults = {
        "milvus_uri": "http://localhost:19530",
        "milvus_token": "root:Milvus",
        "milvus_papers_collection": "papers",
        "milvus_chunks_collection": "paper_chunks",
        "milvus_tables_collection": "paper_tables",
        "milvus_figures_collection": "paper_figures",
        "embedding_dimension": 4,
        "openai_api_key": "sk-test-fake",
        "openai_agent_model": "gpt-5-nano",
        "openai_chat_model": "gpt-5-mini",
    }
    defaults.update(overrides)
    return Settings(**defaults)


# ---------------------------------------------------------------------------
# Test: keyword topic classification
# ---------------------------------------------------------------------------


class TestTopicClassification(unittest.TestCase):
    """Verify the keyword-based fallback classifier."""

    def test_ai_topics(self):
        from app.services.session_service import classify_topic_keyword

        self.assertEqual(classify_topic_keyword("deep learning for images"), "ai")
        self.assertEqual(classify_topic_keyword("transformer architectures"), "ai")
        self.assertEqual(classify_topic_keyword("reinforcement learning in robotics"), "ai")

    def test_healthcare_topics(self):
        from app.services.session_service import classify_topic_keyword

        self.assertEqual(classify_topic_keyword("clinical drug trials"), "healthcare")
        self.assertEqual(classify_topic_keyword("biomedical imaging for diagnosis"), "healthcare")

    def test_social_topics(self):
        from app.services.session_service import classify_topic_keyword

        self.assertEqual(classify_topic_keyword("social media and public opinion"), "social")

    def test_law_topics(self):
        from app.services.session_service import classify_topic_keyword

        self.assertEqual(classify_topic_keyword("intellectual property regulation"), "law")

    def test_general_fallback(self):
        from app.services.session_service import classify_topic_keyword

        self.assertEqual(classify_topic_keyword("quantum entanglement experiments"), "general")


# ---------------------------------------------------------------------------
# Test: SessionService CRUD
# ---------------------------------------------------------------------------


class TestSessionServiceCRUD(unittest.TestCase):
    """Verify in-memory session store create / get / delete."""

    def setUp(self):
        from app.services.session_service import SessionService

        self.svc = SessionService()

    def test_create_and_get(self):
        session = self.svc.create("deep learning", "ai")
        self.assertEqual(session.topic, "deep learning")
        self.assertEqual(session.category, "ai")
        self.assertIsNotNone(self.svc.get(session.session_id))

    def test_delete(self):
        session = self.svc.create("contracts", "law")
        deleted = self.svc.delete(session.session_id)
        self.assertEqual(deleted.session_id, session.session_id)
        self.assertIsNone(self.svc.get(session.session_id))

    def test_delete_nonexistent(self):
        self.assertIsNone(self.svc.delete("does_not_exist"))

    def test_list_sessions(self):
        self.svc.create("topic a", "ai")
        self.svc.create("topic b", "healthcare")
        self.assertEqual(len(self.svc.list_sessions()), 2)


# ---------------------------------------------------------------------------
# Test: full HTTP session lifecycle
# ---------------------------------------------------------------------------


class TestSessionFlowHTTP(unittest.TestCase):
    """End-to-end session lifecycle through FastAPI TestClient.

    All external dependencies (Milvus, arXiv, ingestion, OpenAI) are mocked
    so the test runs without any live services.
    """

    def setUp(self):
        """Patch heavy dependencies and create a TestClient."""
        # --- Patch MilvusStore so no real Milvus connection is attempted -----
        self.mock_milvus = MagicMock()
        self.mock_milvus.healthy.return_value = True
        self.mock_milvus.initialize = AsyncMock()
        self.mock_milvus.merge_session_to_global = AsyncMock()
        self.mock_milvus.drop_session_collections = AsyncMock()

        # --- Patch FilesystemStorage -----------------------------------------
        self.mock_storage = MagicMock()
        self.mock_storage.cleanup_temp_session = AsyncMock()

        # --- Patch IngestionPipeline -----------------------------------------
        from app.models.api import IngestedPaperResult
        from app.ingestion.status import IngestionStatusStore

        self.mock_pipeline = MagicMock()
        mock_job = MagicMock()
        mock_job.papers = [
            IngestedPaperResult(paper_id="p1", title="Paper One", status="ingested", detail="ok"),
            IngestedPaperResult(paper_id="p2", title="Paper Two", status="ingested", detail="ok"),
        ]
        self.mock_pipeline.ingest = AsyncMock(return_value=mock_job)

        # --- Patch AgentCoordinator ------------------------------------------
        self.mock_coordinator = MagicMock()
        self.mock_coordinator.query = AsyncMock(return_value={
            "final_answer": "Test answer from agent pipeline.",
            "retrieval_hits": [],
            "github_repos": [],
            "recommendations": ["Try @buddy for code generation."],
            "drift_warning": None,
        })

        # --- Patch SessionService (use real implementation) ------------------
        from app.services.session_service import SessionService

        self.session_service = SessionService()  # no OpenAI key → keyword fallback

        # --- Wire patches into the route module where names are actually used ---
        import app.api.dependencies as deps
        import app.api.routes.chat as chat_mod

        deps.get_milvus_store.cache_clear()
        deps.get_ingestion_pipeline.cache_clear()
        deps.get_agent_coordinator.cache_clear()
        deps.get_session_service.cache_clear()
        deps.get_filesystem_storage.cache_clear()

        self._patches = [
            # Patch in the chat router module (where `from ... import` binds the names)
            patch.object(chat_mod, "get_milvus_store", return_value=self.mock_milvus),
            patch.object(chat_mod, "get_ingestion_pipeline", return_value=self.mock_pipeline),
            patch.object(chat_mod, "get_agent_coordinator", return_value=self.mock_coordinator),
            patch.object(chat_mod, "get_session_service", return_value=self.session_service),
            patch.object(chat_mod, "get_filesystem_storage", return_value=self.mock_storage),
            # Also patch in dependencies and main for lifespan initialisation
            patch.object(deps, "get_milvus_store", return_value=self.mock_milvus),
            patch("app.main.get_milvus_store", return_value=self.mock_milvus),
        ]
        for p in self._patches:
            p.start()

        from app.main import create_app

        self.client = TestClient(create_app())

    def tearDown(self):
        for p in self._patches:
            p.stop()
        # Restore caches
        import app.api.dependencies as deps
        deps.get_milvus_store.cache_clear()
        deps.get_ingestion_pipeline.cache_clear()
        deps.get_agent_coordinator.cache_clear()
        deps.get_session_service.cache_clear()
        deps.get_filesystem_storage.cache_clear()

    # -- Start session --------------------------------------------------------

    def test_start_session_success(self):
        resp = self.client.post("/chat/sessions", json={"topic": "deep learning for NLP"})
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn("session_id", body)
        self.assertEqual(body["topic"], "deep learning for NLP")
        self.assertEqual(body["category"], "ai")
        self.assertEqual(len(body["papers"]), 2)

        # Verify ingestion was called with session_id
        call_kwargs = self.mock_pipeline.ingest.call_args
        self.assertEqual(call_kwargs.kwargs["session_id"], body["session_id"])

    def test_start_session_topic_too_short(self):
        resp = self.client.post("/chat/sessions", json={"topic": "ab"})
        self.assertEqual(resp.status_code, 422)

    def test_start_session_general_category(self):
        resp = self.client.post("/chat/sessions", json={"topic": "quantum entanglement"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["category"], "general")

    # -- Query with session context ------------------------------------------

    def test_query_with_session_enrichment(self):
        # First create a session.
        create_resp = self.client.post("/chat/sessions", json={"topic": "clinical drug trials"})
        session_id = create_resp.json()["session_id"]

        # Query without explicitly providing topic/category.
        query_resp = self.client.post("/chat/query", json={
            "question": "What are the phases of clinical trials?",
            "session_id": session_id,
        })
        self.assertEqual(query_resp.status_code, 200)
        body = query_resp.json()
        self.assertEqual(body["answer"], "Test answer from agent pipeline.")

        # Verify the coordinator received enriched context.
        call_kwargs = self.mock_coordinator.query.call_args
        self.assertEqual(call_kwargs.kwargs["session_id"], session_id)
        self.assertEqual(call_kwargs.kwargs["session_topic"], "clinical drug trials")
        self.assertEqual(call_kwargs.kwargs["category"], "healthcare")

    def test_query_without_session(self):
        resp = self.client.post("/chat/query", json={
            "question": "What is attention in transformers?",
        })
        self.assertEqual(resp.status_code, 200)

    # -- End session ---------------------------------------------------------

    def test_end_session_success(self):
        create_resp = self.client.post("/chat/sessions", json={"topic": "patent law overview"})
        session_id = create_resp.json()["session_id"]

        end_resp = self.client.post(f"/chat/sessions/{session_id}/end")
        self.assertEqual(end_resp.status_code, 200)
        body = end_resp.json()
        self.assertEqual(body["session_id"], session_id)
        self.assertEqual(body["category"], "law")
        self.assertEqual(body["status"], "ended")

        # Verify merge, drop, and cleanup were called.
        self.mock_milvus.merge_session_to_global.assert_called_once_with(session_id, "law")
        self.mock_milvus.drop_session_collections.assert_called_once_with(session_id)
        self.mock_storage.cleanup_temp_session.assert_called_once_with(session_id)

        # Verify session is gone.
        self.assertIsNone(self.session_service.get(session_id))

    def test_end_nonexistent_session_returns_404(self):
        resp = self.client.post("/chat/sessions/nonexistent/end")
        self.assertEqual(resp.status_code, 404)

    # -- Full lifecycle -------------------------------------------------------

    def test_full_lifecycle(self):
        """Create → Query → End in sequence."""
        # Create
        create = self.client.post("/chat/sessions", json={"topic": "social media bias research"})
        self.assertEqual(create.status_code, 200)
        sid = create.json()["session_id"]
        self.assertEqual(create.json()["category"], "social")

        # Query
        query = self.client.post("/chat/query", json={
            "question": "How does algorithmic bias spread on social platforms?",
            "session_id": sid,
        })
        self.assertEqual(query.status_code, 200)

        # End
        end = self.client.post(f"/chat/sessions/{sid}/end")
        self.assertEqual(end.status_code, 200)
        self.assertEqual(end.json()["status"], "ended")

        # Session should no longer exist
        end_again = self.client.post(f"/chat/sessions/{sid}/end")
        self.assertEqual(end_again.status_code, 404)


if __name__ == "__main__":
    unittest.main()
