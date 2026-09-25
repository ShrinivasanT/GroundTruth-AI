from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.chat import router as chat_router
from app.api.routes.health import router as health_router
from app.api.routes.papers import router as papers_router
from app.api.dependencies import get_milvus_store
from app.core.config import get_settings
from app.core.logging import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    store = get_milvus_store()
    await store.initialize()

    # Start the background session reaper task
    from app.api.routes.chat import start_session_reaper
    reaper_task = start_session_reaper()

    yield

    # Cancel the background session reaper task on shutdown
    if reaper_task:
        reaper_task.cancel()


def create_app() -> FastAPI:
    app = FastAPI(
        title="FactChat Backend",
        version="0.1.0",
        description="Production-grade multimodal RAG backend for scientific papers.",
        lifespan=lifespan,
    )
    app.include_router(health_router)
    app.include_router(papers_router)
    app.include_router(chat_router)
    return app


app = create_app()
