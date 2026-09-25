"""Tests for MilvusStore dynamic session collection lifecycle.

These tests exercise the session-aware collection provisioning, upsert,
search, merge-to-global, and drop routines added in Phase 1.

They use ``unittest.mock`` to patch the underlying ``MilvusClient`` so
no live Milvus instance is required.
"""

import asyncio
import unittest
from unittest.mock import MagicMock, patch

from pymilvus import MilvusClient

from app.core.config import Settings
from app.vectorstores.milvus_store import MilvusStore, VALID_CATEGORIES


def _make_settings(**overrides) -> Settings:
    """Create a Settings instance with sensible test defaults."""
    defaults = {
        "milvus_uri": "http://localhost:19530",
        "milvus_token": "root:Milvus",
        "milvus_papers_collection": "papers",
        "milvus_chunks_collection": "paper_chunks",
        "milvus_tables_collection": "paper_tables",
        "milvus_figures_collection": "paper_figures",
        "embedding_dimension": 4,
    }
    defaults.update(overrides)
    return Settings(**defaults)


class TestNormalizeCategory(unittest.TestCase):
    """Test _normalize_category clamps to valid values."""

    def test_known_categories(self):
        store = MilvusStore.__new__(MilvusStore)
        for cat in VALID_CATEGORIES:
            self.assertEqual(store._normalize_category(cat), cat)
            self.assertEqual(store._normalize_category(cat.upper()), cat)
            self.assertEqual(store._normalize_category(f"  {cat}  "), cat)

    def test_unknown_category_falls_back_to_general(self):
        store = MilvusStore.__new__(MilvusStore)
        self.assertEqual(store._normalize_category("quantum_physics"), "general")
        self.assertEqual(store._normalize_category(""), "general")


class TestResolveCollectionName(unittest.TestCase):
    """Test _resolve_collection_name routing logic."""

    def setUp(self):
        self.store = MilvusStore.__new__(MilvusStore)
        self.store._settings = _make_settings()

    def test_default_uses_settings(self):
        self.assertEqual(
            self.store._resolve_collection_name("chunks"),
            "paper_chunks",
        )

    def test_session_id_takes_precedence(self):
        self.assertEqual(
            self.store._resolve_collection_name(
                "chunks", session_id="abc123", category="ai",
            ),
            "sess_abc123_chunks",
        )

    def test_category_routing(self):
        self.assertEqual(
            self.store._resolve_collection_name("tables", category="Healthcare"),
            "global_healthcare_tables",
        )

    def test_unknown_category_routes_to_general(self):
        self.assertEqual(
            self.store._resolve_collection_name("figures", category="robotics"),
            "global_general_figures",
        )


@patch("app.vectorstores.milvus_store.MilvusClient")
class TestSessionUpsert(unittest.TestCase):
    """Upserts with a session_id should target the session-prefixed collection
    and auto-provision it if it does not exist."""

    def setUp(self):
        self.settings = _make_settings()

    def test_upsert_chunks_provisions_and_upserts(self, MockClient):
        mock_client = MockClient.return_value
        mock_client.has_collection.return_value = False
        mock_client.create_schema = MilvusClient.create_schema
        mock_client.prepare_index_params.return_value = MagicMock()

        store = MilvusStore(self.settings)
        from app.models.domain import ChunkRecord

        record = ChunkRecord(
            chunk_id="c1",
            paper_id="p1",
            title="Test",
            section="intro",
            text="hello world",
            page=1,
            embedding=[0.1, 0.2, 0.3, 0.4],
        )

        asyncio.run(store.upsert_chunks([record], session_id="sess001"))

        # Verify collection name is session-prefixed
        upsert_call = mock_client.upsert.call_args
        self.assertEqual(upsert_call.kwargs["collection_name"], "sess_sess001_chunks")


@patch("app.vectorstores.milvus_store.MilvusClient")
class TestSessionSearch(unittest.TestCase):
    """Search with session_id / category routes to the correct collection and
    returns [] when the collection does not exist."""

    def setUp(self):
        self.settings = _make_settings()

    def test_search_missing_collection_returns_empty(self, MockClient):
        mock_client = MockClient.return_value
        mock_client.has_collection.return_value = False

        store = MilvusStore(self.settings)
        results = asyncio.run(
            store.search_chunks([0.0] * 4, 5, session_id="nonexistent"),
        )
        self.assertEqual(results, [])
        mock_client.search.assert_not_called()

    def test_search_existing_session_collection(self, MockClient):
        mock_client = MockClient.return_value
        mock_client.has_collection.return_value = True
        mock_client.search.return_value = [
            [{"entity": {"chunk_id": "c1", "text": "hi"}, "distance": 0.9}],
        ]

        store = MilvusStore(self.settings)
        results = asyncio.run(
            store.search_chunks([0.0] * 4, 5, session_id="sess002"),
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["chunk_id"], "c1")
        self.assertAlmostEqual(results[0]["score"], 0.9)

        call_args = mock_client.search.call_args
        self.assertEqual(call_args.kwargs["collection_name"], "sess_sess002_chunks")


@patch("app.vectorstores.milvus_store.MilvusClient")
class TestMergeAndDrop(unittest.TestCase):
    """Verify merge_session_to_global and drop_session_collections."""

    def setUp(self):
        self.settings = _make_settings()

    def test_merge_copies_records(self, MockClient):
        mock_client = MockClient.return_value
        # Session collections exist; global collections do not.
        mock_client.has_collection.side_effect = lambda collection_name: collection_name.startswith("sess_")
        mock_client.create_schema = MilvusClient.create_schema
        mock_client.prepare_index_params.return_value = MagicMock()

        sample_records = [
            {"chunk_id": "c1", "paper_id": "p1", "title": "T", "section": "s",
             "text": "t", "page": 1, "embedding": [0.1, 0.2, 0.3, 0.4]},
        ]
        mock_client.query.return_value = sample_records

        store = MilvusStore(self.settings)
        asyncio.run(store.merge_session_to_global("sess003", "AI"))

        # Verify upsert was called targeting the global_ai_* collection.
        upsert_calls = mock_client.upsert.call_args_list
        dst_names = [c.kwargs["collection_name"] for c in upsert_calls]
        self.assertIn("global_ai_chunks", dst_names)

    def test_drop_removes_collections(self, MockClient):
        mock_client = MockClient.return_value
        mock_client.has_collection.return_value = True

        store = MilvusStore(self.settings)
        asyncio.run(store.drop_session_collections("sess004"))

        dropped = [
            c.kwargs["collection_name"]
            for c in mock_client.drop_collection.call_args_list
        ]
        self.assertIn("sess_sess004_chunks", dropped)
        self.assertIn("sess_sess004_tables", dropped)
        self.assertIn("sess_sess004_figures", dropped)


if __name__ == "__main__":
    unittest.main()
