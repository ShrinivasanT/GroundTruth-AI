"""Tests for the Phase 3 LangGraph agent pipeline.

These tests exercise:
- Input routing (default path vs. @agent tags)
- Retriever node state updates
- Refetch decision logic (threshold, session_id guard, single-cycle guard)
- Repo enrichment regex parsing
- Recommendation node output structure
- Full coordinator orchestration with mocked dependencies
"""

import asyncio
import json
import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from app.agents.state import AgentState, RepoInfo, RecommendationResult
from app.models.domain import RetrievalHit, RetrievalSource


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_hit(
    label: str = "C1",
    score: float = 0.85,
    content: str = "sample content",
    title: str = "Test Paper",
) -> RetrievalHit:
    return RetrievalHit(
        source=RetrievalSource.CHUNK,
        source_id=f"chunk_{label}",
        paper_id="paper_001",
        title=title,
        content=content,
        section="intro",
        page=1,
        score=score,
        citation_label=label,
    )


def _make_settings(**overrides) -> MagicMock:
    """Create a mock Settings object with sensible defaults."""
    s = MagicMock()
    s.openai_api_key = "sk-test-key"
    s.openai_agent_model = "gpt-5-nano"
    s.openai_chat_model = "gpt-5-mini"
    s.refetch_relevance_threshold = 0.65
    s.refetch_paper_limit = 2
    for k, v in overrides.items():
        setattr(s, k, v)
    return s


# =====================================================================
# 1. Routing
# =====================================================================


class TestRouteInput(unittest.TestCase):
    """Verify that _route_input correctly detects @agent tags."""

    def test_default_path(self):
        from app.agents.graph import _route_input
        state: AgentState = {"query": "What is attention mechanism?"}
        self.assertEqual(_route_input(state), "retrieve")

    def test_buddy_tag(self):
        from app.agents.graph import _route_input
        state: AgentState = {"query": "@buddy implement softmax in PyTorch"}
        self.assertEqual(_route_input(state), "buddy_placeholder")

    def test_review_tag(self):
        from app.agents.graph import _route_input
        state: AgentState = {"query": "@review summarize findings"}
        self.assertEqual(_route_input(state), "review_placeholder")

    def test_writer_tag(self):
        from app.agents.graph import _route_input
        state: AgentState = {"query": "@writer build docs"}
        self.assertEqual(_route_input(state), "writer_placeholder")

    def test_tag_case_insensitive(self):
        from app.agents.graph import _route_input
        state: AgentState = {"query": "@BUDDY generate code"}
        self.assertEqual(_route_input(state), "buddy_placeholder")


# =====================================================================
# 2. Retriever Node
# =====================================================================


class TestRetrieverNode(unittest.TestCase):
    """Verify that the retriever node populates hits and scores."""

    def test_returns_hits_and_scores(self):
        from app.agents.retriever_agent import make_retrieve_node

        mock_retriever = MagicMock()
        hits = [_make_hit("C1", 0.9), _make_hit("C2", 0.75)]
        mock_retriever.retrieve = AsyncMock(return_value=hits)

        node = make_retrieve_node(mock_retriever)
        state: AgentState = {
            "query": "What is BERT?",
            "top_k": 5,
            "session_id": "sess_001",
            "category": None,
        }
        result = asyncio.run(node(state))
        self.assertEqual(len(result["retrieval_hits"]), 2)
        self.assertAlmostEqual(result["relevance_scores"][0], 0.9)
        self.assertAlmostEqual(result["relevance_scores"][1], 0.75)

    def test_empty_results(self):
        from app.agents.retriever_agent import make_retrieve_node

        mock_retriever = MagicMock()
        mock_retriever.retrieve = AsyncMock(return_value=[])

        node = make_retrieve_node(mock_retriever)
        state: AgentState = {"query": "something obscure", "top_k": 5}
        result = asyncio.run(node(state))
        self.assertEqual(result["retrieval_hits"], [])
        self.assertEqual(result["relevance_scores"], [])


# =====================================================================
# 3. Refetch Decision
# =====================================================================


class TestRefetchDecision(unittest.TestCase):
    """Verify the conditional edge logic for triggering refetch."""

    @patch("app.agents.graph.get_settings")
    def test_triggers_on_low_score(self, mock_settings_fn):
        mock_settings_fn.return_value = _make_settings()
        from app.agents.graph import _refetch_decision

        state: AgentState = {
            "relevance_scores": [0.3, 0.2],
            "refetch_count": 0,
            "session_id": "sess_001",
        }
        self.assertEqual(_refetch_decision(state), "refetch")

    @patch("app.agents.graph.get_settings")
    def test_triggers_on_empty_scores(self, mock_settings_fn):
        mock_settings_fn.return_value = _make_settings()
        from app.agents.graph import _refetch_decision

        state: AgentState = {
            "relevance_scores": [],
            "refetch_count": 0,
            "session_id": "sess_001",
        }
        self.assertEqual(_refetch_decision(state), "refetch")

    @patch("app.agents.graph.get_settings")
    def test_skips_when_scores_above_threshold(self, mock_settings_fn):
        mock_settings_fn.return_value = _make_settings()
        from app.agents.graph import _refetch_decision

        state: AgentState = {
            "relevance_scores": [0.85, 0.70],
            "refetch_count": 0,
            "session_id": "sess_001",
        }
        self.assertEqual(_refetch_decision(state), "repo_enrich")

    @patch("app.agents.graph.get_settings")
    def test_skips_when_already_refetched(self, mock_settings_fn):
        mock_settings_fn.return_value = _make_settings()
        from app.agents.graph import _refetch_decision

        state: AgentState = {
            "relevance_scores": [0.3],
            "refetch_count": 1,  # already refetched once
            "session_id": "sess_001",
        }
        self.assertEqual(_refetch_decision(state), "repo_enrich")

    @patch("app.agents.graph.get_settings")
    def test_skips_when_no_session(self, mock_settings_fn):
        mock_settings_fn.return_value = _make_settings()
        from app.agents.graph import _refetch_decision

        state: AgentState = {
            "relevance_scores": [0.3],
            "refetch_count": 0,
            "session_id": None,  # no session — can't micro-ingest
        }
        self.assertEqual(_refetch_decision(state), "repo_enrich")


# =====================================================================
# 4. Repo Agent Regex
# =====================================================================


class TestRepoAgentRegex(unittest.TestCase):
    """Verify GitHub URL regex extraction from citation content."""

    def test_extracts_github_urls(self):
        from app.agents.repo_agent import _GITHUB_PATTERN

        text = "Our code is at https://github.com/google-research/bert and also github.com/huggingface/transformers."
        matches = _GITHUB_PATTERN.findall(text)
        owners = [m[0] for m in matches]
        # Strip trailing punctuation the same way the node does.
        repos = [m[1].rstrip(".,;:)") for m in matches]
        self.assertIn("google-research", owners)
        self.assertIn("huggingface", owners)
        self.assertIn("bert", repos)
        self.assertIn("transformers", repos)

    def test_no_github_url(self):
        from app.agents.repo_agent import _GITHUB_PATTERN

        text = "This paper does not reference any repository."
        matches = _GITHUB_PATTERN.findall(text)
        self.assertEqual(len(matches), 0)


class TestRepoEnrichNode(unittest.TestCase):
    """Verify the repo enrichment node handles API responses."""

    def test_returns_empty_on_no_hits(self):
        from app.agents.repo_agent import make_repo_enrich_node

        mock_client = MagicMock()
        node = make_repo_enrich_node(mock_client)
        state: AgentState = {"retrieval_hits": []}
        result = asyncio.run(node(state))
        self.assertEqual(result["github_repos"], [])

    def test_returns_empty_when_no_github_patterns(self):
        from app.agents.repo_agent import make_repo_enrich_node

        mock_client = MagicMock()
        node = make_repo_enrich_node(mock_client)
        state: AgentState = {
            "retrieval_hits": [_make_hit(content="No repo references here.")],
        }
        result = asyncio.run(node(state))
        self.assertEqual(result["github_repos"], [])


# =====================================================================
# 5. Recommendation Result Model
# =====================================================================


class TestRecommendationResult(unittest.TestCase):
    """Verify the RecommendationResult Pydantic model."""

    def test_default_values(self):
        r = RecommendationResult()
        self.assertEqual(r.follow_ups, [])
        self.assertFalse(r.drift_detected)

    def test_from_json(self):
        data = {
            "follow_ups": ["Q1", "Q2"],
            "agent_suggestions": ["Use @buddy"],
            "drift_detected": True,
            "new_session_recommended": True,
            "drift_message": "Your query has drifted.",
        }
        r = RecommendationResult(**data)
        self.assertTrue(r.drift_detected)
        self.assertEqual(len(r.follow_ups), 2)


# =====================================================================
# 6. Coordinator API Key Validation
# =====================================================================


class TestCoordinatorInit(unittest.TestCase):
    """Verify that the coordinator raises on missing API key."""

    def test_raises_without_api_key(self):
        # Mock all heavy third-party modules that the import chain touches.
        docling_mock = MagicMock()
        fastembed_mock = MagicMock()
        modules_to_mock = {
            "fastembed": fastembed_mock,
            "docling": docling_mock,
            "docling.datamodel": docling_mock,
            "docling.datamodel.base_models": docling_mock,
            "docling.datamodel.pipeline_options": docling_mock,
            "docling.document_converter": docling_mock,
            "docling_core": docling_mock,
            "docling_core.types": docling_mock,
            "docling_core.types.doc": docling_mock,
        }
        with patch.dict("sys.modules", modules_to_mock):
            # Force reimport so the mocked modules are used.
            import importlib
            import app.agents.agent_coordinator as coord_mod
            importlib.reload(coord_mod)

            settings = _make_settings(openai_api_key=None)
            with self.assertRaises(RuntimeError) as ctx:
                coord_mod.AgentCoordinator(
                    settings=settings,
                    retriever=MagicMock(),
                    http_client=MagicMock(),
                    arxiv_client=MagicMock(),
                    ingestion_pipeline=MagicMock(),
                )
            self.assertIn("OPENAI_API_KEY", str(ctx.exception))


# =====================================================================
# 7. Callable Specialty Agents
# =====================================================================


class TestCallableAgents(unittest.TestCase):
    """Verify specialty agent nodes perform clean tag trimming, retrieval, and LLM compilation."""

    def setUp(self):
        self.settings = _make_settings()
        self.mock_retriever = MagicMock()
        self.mock_retriever.retrieve = AsyncMock(
            return_value=[_make_hit("C1", 0.9, "Deep learning architecture contents.")]
        )

    @patch("app.agents.callable_agents.run_code_in_sandbox")
    @patch("app.agents.callable_agents.ChatOpenAI")
    def test_buddy_agent_success(self, mock_llm_class, mock_sandbox):
        from app.agents.callable_agents import make_buddy_node

        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(
            return_value=MagicMock(content="Here is PyTorch Softmax...\n```python\nprint('hello')\n```")
        )
        mock_llm_class.return_value = mock_llm

        mock_sandbox.return_value = {
            "success": True,
            "stdout": "hello\n",
            "stderr": "",
            "exit_code": 0
        }

        buddy_node = make_buddy_node(self.settings, self.mock_retriever)
        state: AgentState = {"query": "@buddy implement Softmax"}

        result = asyncio.run(buddy_node(state))

        # Verify query tag was trimmed before retrieval
        self.mock_retriever.retrieve.assert_called_once()
        args = self.mock_retriever.retrieve.call_args[0]
        self.assertEqual(args[0], "implement Softmax")

        # Verify state outputs
        self.assertIn("Here is PyTorch Softmax...", result["final_answer"])
        self.assertIn("Sandbox Verification Log", result["final_answer"])
        self.assertIn("Status: SUCCESS", result["final_answer"])
        self.assertEqual(len(result["retrieval_hits"]), 1)
        self.assertEqual(result["relevance_scores"], [0.9])

    @patch("app.agents.callable_agents.run_code_in_sandbox")
    @patch("app.agents.callable_agents.ChatOpenAI")
    def test_buddy_agent_self_correction(self, mock_llm_class, mock_sandbox):
        from app.agents.callable_agents import make_buddy_node

        mock_llm = MagicMock()
        # First return buggy code, then corrected code
        mock_llm.ainvoke = AsyncMock(
            side_effect=[
                MagicMock(content="Attempt 1 code:\n```python\nprint(undefined_var)\n```"),
                MagicMock(content="Attempt 2 code:\n```python\nprint('fixed')\n```")
            ]
        )
        mock_llm_class.return_value = mock_llm

        # First execution fails, second succeeds
        mock_sandbox.side_effect = [
            {
                "success": False,
                "stdout": "",
                "stderr": "NameError: name 'undefined_var' is not defined",
                "exit_code": 1
            },
            {
                "success": True,
                "stdout": "fixed\n",
                "stderr": "",
                "exit_code": 0
            }
        ]

        buddy_node = make_buddy_node(self.settings, self.mock_retriever)
        state: AgentState = {"query": "@buddy write code"}

        result = asyncio.run(buddy_node(state))

        # Verify we executed sandbox twice (first failed, second succeeded)
        self.assertEqual(mock_sandbox.call_count, 2)
        # Verify corrected output and successful log are present
        self.assertIn("Attempt 2 code:", result["final_answer"])
        self.assertIn("Status: SUCCESS", result["final_answer"])

    @patch("app.agents.callable_agents.ChatOpenAI")
    def test_review_agent(self, mock_llm_class):
        from app.agents.callable_agents import make_review_node

        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(
            return_value=MagicMock(content="### Executive Summary\nMethodology review...")
        )
        mock_llm_class.return_value = mock_llm

        review_node = make_review_node(self.settings, self.mock_retriever)
        state: AgentState = {
            "query": "@review critique research",
            "session_topic": "Machine Learning"
        }

        result = asyncio.run(review_node(state))

        # Verify tag trimmed from search
        self.mock_retriever.retrieve.assert_called_once_with(
            "critique research", 8, session_id=None, category=None
        )
        self.assertEqual(result["final_answer"], "### Executive Summary\nMethodology review...")

    @patch("app.agents.callable_agents.ChatOpenAI")
    def test_writer_agent(self, mock_llm_class):
        from app.agents.callable_agents import make_writer_node

        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(
            return_value=MagicMock(content="## Specifications\nDesign doc info...")
        )
        mock_llm_class.return_value = mock_llm

        writer_node = make_writer_node(self.settings, self.mock_retriever)
        state: AgentState = {
            "query": "@writer generate specs",
            "session_id": "test_sess_99"
        }

        result = asyncio.run(writer_node(state))

        # Verify output saved file block is appended
        self.assertIn("## Specifications\nDesign doc info...", result["final_answer"])
        self.assertIn("📄 Programmatic Word Export", result["final_answer"])
        self.assertIn("doc_test_sess_99_", result["final_answer"])

        # Clean up generated doc file from storage/temp/ if it was created
        temp_dir = os.path.join("storage", "temp")
        if os.path.exists(temp_dir):
            for f in os.listdir(temp_dir):
                if f.startswith("doc_test_sess_99_") and f.endswith(".docx"):
                    try:
                        os.remove(os.path.join(temp_dir, f))
                    except Exception:
                        pass


# =====================================================================
# 8. RepoInfo Model
# =====================================================================


class TestRepoInfoModel(unittest.TestCase):
    """Verify the RepoInfo Pydantic model."""

    def test_serialization(self):
        info = RepoInfo(
            owner="google",
            name="bert",
            description="BERT implementation",
            stars=30000,
            language="Python",
            topics=["nlp", "transformer"],
            html_url="https://github.com/google/bert",
        )
        data = info.model_dump()
        self.assertEqual(data["owner"], "google")
        self.assertEqual(data["stars"], 30000)
        self.assertIsInstance(data["topics"], list)


if __name__ == "__main__":
    unittest.main()
