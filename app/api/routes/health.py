from fastapi import APIRouter

from app.api.dependencies import get_milvus_store
from app.models.api import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    milvus = get_milvus_store()
    return HealthResponse(status="ok", milvus="ok" if milvus.healthy() else "unavailable")
