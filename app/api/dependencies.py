from functools import lru_cache

import httpx

from app.core.config import get_settings
from app.embeddings.fastembed_service import FastEmbedService
from app.ingestion.pipeline import IngestionPipeline
from app.ingestion.status import IngestionStatusStore
from app.llm.openrouter_service import OpenRouterAnswerService
from app.parsers.docling_parser import DoclingParser
from app.retrieval.service import HybridRetriever
from app.llm.groq_service import GroqSemanticService
from app.services.arxiv_client import ArxivClient
from app.services.huggingface_client import HuggingFaceClient
from app.services.paper_service import PaperDiscoveryService
from app.storage.filesystem import FilesystemStorage
from app.vectorstores.milvus_store import MilvusStore


@lru_cache(maxsize=1)
def get_http_client() -> httpx.AsyncClient:
    settings = get_settings()
    limits = httpx.Limits(
        max_connections=settings.http_max_connections,
        max_keepalive_connections=settings.http_max_keepalive_connections,
    )
    return httpx.AsyncClient(timeout=settings.request_timeout_seconds, limits=limits, follow_redirects=True)


@lru_cache(maxsize=1)
def get_milvus_store() -> MilvusStore:
    return MilvusStore(get_settings())


@lru_cache(maxsize=1)
def get_embeddings() -> FastEmbedService:
    return FastEmbedService(get_settings())


@lru_cache(maxsize=1)
def get_status_store() -> IngestionStatusStore:
    return IngestionStatusStore()


@lru_cache(maxsize=1)
def get_arxiv_client() -> ArxivClient:
    return ArxivClient(get_http_client(), get_settings())


@lru_cache(maxsize=1)
def get_huggingface_client() -> HuggingFaceClient:
    return HuggingFaceClient(get_http_client(), get_settings())


@lru_cache(maxsize=1)
def get_groq_service() -> GroqSemanticService:
    return GroqSemanticService(get_settings())


@lru_cache(maxsize=1)
def get_discovery_service() -> PaperDiscoveryService:
    return PaperDiscoveryService(
        arxiv_client=get_arxiv_client(),
        huggingface_client=get_huggingface_client(),
        groq_service=get_groq_service(),
    )


@lru_cache(maxsize=1)
def get_ingestion_pipeline() -> IngestionPipeline:
    settings = get_settings()
    http_client = get_http_client()
    return IngestionPipeline(
        discovery=get_discovery_service(),
        storage=FilesystemStorage(settings, http_client),
        parser=DoclingParser(settings),
        embeddings=get_embeddings(),
        milvus=get_milvus_store(),
        status_store=get_status_store(),
        concurrency=settings.ingestion_concurrency,
    )


@lru_cache(maxsize=1)
def get_retriever() -> HybridRetriever:
    return HybridRetriever(get_embeddings(), get_milvus_store())


@lru_cache(maxsize=1)
def get_answer_service() -> OpenRouterAnswerService:
    return OpenRouterAnswerService(get_settings())


@lru_cache(maxsize=1)
def get_agent_coordinator():
    """Build and cache the AgentCoordinator singleton.

    Raises ``RuntimeError`` if ``OPENAI_API_KEY`` is not configured.
    """
    from app.agents.agent_coordinator import AgentCoordinator

    settings = get_settings()
    return AgentCoordinator(
        settings=settings,
        retriever=get_retriever(),
        http_client=get_http_client(),
        arxiv_client=get_arxiv_client(),
        ingestion_pipeline=get_ingestion_pipeline(),
    )


@lru_cache(maxsize=1)
def get_session_service():
    """Build and cache the SessionService singleton."""
    from app.services.session_service import SessionService

    settings = get_settings()
    return SessionService(
        openai_api_key=settings.openai_api_key,
        openai_model=settings.openai_agent_model,
    )


@lru_cache(maxsize=1)
def get_filesystem_storage() -> FilesystemStorage:
    settings = get_settings()
    return FilesystemStorage(settings, get_http_client())

