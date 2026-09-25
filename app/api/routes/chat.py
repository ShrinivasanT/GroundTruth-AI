"""Chat router — session management and agentic query pipeline.

Endpoints
---------
POST /chat/sessions
    Start a new learning session by providing a topic.
POST /chat/query
    Send a query through the LangGraph agent pipeline.
POST /chat/sessions/{session_id}/end
    Merge session vectors to global DB, drop session collections, clean temp files.
"""

from __future__ import annotations

import asyncio
import logging
import time

from fastapi import APIRouter, HTTPException, BackgroundTasks

from app.api.dependencies import (
    get_agent_coordinator,
    get_filesystem_storage,
    get_ingestion_pipeline,
    get_milvus_store,
    get_session_service,
)
from app.models.api import (
    ChatQueryRequest,
    ChatQueryResponse,
    EndSessionResponse,
    IngestPapersRequest,
    SessionResponse,
    StartSessionRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


# ---------------------------------------------------------------------------
# POST /chat/sessions — create a new learning session
# ---------------------------------------------------------------------------


@router.post("/sessions", response_model=SessionResponse)
async def start_session(
    request: StartSessionRequest,
    background_tasks: BackgroundTasks,
) -> SessionResponse:
    """Classify the topic, queue ingestion of 15 arXiv papers in the background,
    and return the new session metadata immediately."""
    session_service = get_session_service()
    pipeline = get_ingestion_pipeline()

    # 1. Classify the topic into a canonical category.
    category = await session_service.classify(request.topic)

    # 2. Create the session record (generates a unique session_id).
    session = session_service.create(topic=request.topic, category=category)

    # Check if this is a global Xavier Files session (topic is 'ai', 'healthcare', or 'social')
    is_xavier_session = request.topic.lower() in {"ai", "healthcare", "social"}

    if not is_xavier_session:
        session.ingestion_status = "running"
        logger.info(
            "StartSession: session=%s  topic=%r  category=%s — queuing background ingestion of 15 papers.",
            session.session_id,
            request.topic,
            category,
        )

        async def run_ingestion():
            ingest_request = IngestPapersRequest(query=request.topic, limit=2)
            try:
                job = await pipeline.ingest(ingest_request, session_id=session.session_id)
                paper_results = [p.model_dump() for p in job.papers]
                session.paper_results = paper_results
                session.ingestion_status = "completed"
                logger.info("StartSession: background ingestion completed for session %s", session.session_id)
            except Exception:
                session.ingestion_status = "failed"
                logger.exception("StartSession: background ingestion failed for session %s", session.session_id)

        background_tasks.add_task(run_ingestion)
    else:
        logger.info(
            "StartSession: session=%s  topic=%r  category=%s — Xavier Files session. Connecting directly without processing.",
            session.session_id,
            request.topic,
            category,
        )

    return SessionResponse(
        session_id=session.session_id,
        topic=session.topic,
        category=session.category,
        papers=[],
        ingestion_status=session.ingestion_status,
    )


# ---------------------------------------------------------------------------
# GET /chat/sessions/{session_id} — get active session details
# ---------------------------------------------------------------------------


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str) -> SessionResponse:
    """Get the current details of an active session, including paper results and ingestion status."""
    session_service = get_session_service()
    session = session_service.get(session_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Session '{session_id}' not found or has been terminated.",
        )
    return SessionResponse(
        session_id=session.session_id,
        topic=session.topic,
        category=session.category,
        papers=session.paper_results,
        ingestion_status=session.ingestion_status,
    )


# ---------------------------------------------------------------------------
# POST /chat/query — agentic RAG query
# ---------------------------------------------------------------------------


@router.post("/query", response_model=ChatQueryResponse)
async def query_chat(request: ChatQueryRequest) -> ChatQueryResponse:
    """Route a user query through the LangGraph agent pipeline.

    If a ``session_id`` is supplied the endpoint automatically populates
    ``session_topic`` and ``category`` from the active session record so
    the caller does not need to repeat them.
    """
    coordinator = get_agent_coordinator()
    session_service = get_session_service()

    # Enrich request context from the active session if available.
    session_topic = request.session_topic
    category = request.category

    if request.session_id:
        session = session_service.get(request.session_id)
        if not session:
            raise HTTPException(
                status_code=404,
                detail=f"Session '{request.session_id}' not found or has been terminated.",
            )
        session_topic = session_topic or session.topic
        category = category or session.category

    result = await coordinator.query(
        query=request.question,
        top_k=request.top_k,
        session_id=request.session_id,
        category=category,
        session_topic=session_topic,
    )
    return ChatQueryResponse(
        answer=result.get("final_answer", ""),
        citations=result.get("retrieval_hits", []),
        repos=result.get("github_repos", []),
        recommendations=result.get("recommendations", []),
        drift_warning=result.get("drift_warning"),
    )


# ---------------------------------------------------------------------------
# POST /chat/sessions/{session_id}/end — teardown a learning session
# ---------------------------------------------------------------------------


@router.post("/sessions/{session_id}/end", response_model=EndSessionResponse)
async def end_session(session_id: str) -> EndSessionResponse:
    """Merge session vectors into the global category DB, drop session
    collections, clean up temporary files, and remove the session record."""
    session_service = get_session_service()
    milvus = get_milvus_store()
    storage = get_filesystem_storage()

    session = session_service.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")

    category = session.category

    logger.info(
        "EndSession: session=%s  category=%s — merging, dropping, cleaning.",
        session_id,
        category,
    )

    # 1. Merge session vectors → global category collections.
    await milvus.merge_session_to_global(session_id, category)

    # 2. Drop session-scoped collections.
    await milvus.drop_session_collections(session_id)

    # 3. Delete temporary files for this session.
    await storage.cleanup_temp_session(session_id)

    # 4. Evict the session from the in-memory store.
    session_service.delete(session_id)

    return EndSessionResponse(
        session_id=session_id,
        category=category,
        status="ended",
    )


def start_session_reaper() -> asyncio.Task:
    """Start the background reaper task to clean up inactive sessions (> 5 minutes)."""

    async def reaper_loop():
        logger.info("Session reaper background task started.")
        while True:
            try:
                await asyncio.sleep(10)  # Check every 10 seconds
                session_service = get_session_service()
                milvus = get_milvus_store()
                storage = get_filesystem_storage()

                sessions = session_service.list_sessions()
                now = time.time()
                for session in sessions:
                    # Inactive for more than 5 minutes (300 seconds)
                    if now - session.last_activity > 300:
                        logger.info(
                            "SessionReaper: session %s (%s) has been inactive for %d seconds — auto-terminating and merging.",
                            session.session_id,
                            session.topic,
                            int(now - session.last_activity),
                        )
                        try:
                            # 1. Merge vectors to global
                            await milvus.merge_session_to_global(session.session_id, session.category)
                            # 2. Drop session-scoped collections (does nothing for Xavier sessions since they resolved to global)
                            await milvus.drop_session_collections(session.session_id)
                            # 3. Clean temporary session files
                            await storage.cleanup_temp_session(session.session_id)
                            # 4. Remove session from store
                            session_service.delete(session.session_id)
                        except Exception:
                            logger.exception("SessionReaper: failed to auto-terminate session %s", session.session_id)
            except asyncio.CancelledError:
                logger.info("Session reaper background task cancelled.")
                break
            except Exception:
                logger.exception("SessionReaper: error in reaper loop")

    return asyncio.create_task(reaper_loop())
