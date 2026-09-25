from fastapi import APIRouter, HTTPException

from app.api.dependencies import get_discovery_service, get_ingestion_pipeline, get_status_store
from app.models.api import (
    IngestionResponse,
    IngestionStatusResponse,
    IngestPapersRequest,
    LatestPapersRequest,
    PapersResponse,
    SearchPapersRequest,
)

router = APIRouter(prefix="/papers", tags=["papers"])


@router.post("/search", response_model=PapersResponse)
async def search_papers(request: SearchPapersRequest) -> PapersResponse:
    papers = await get_discovery_service().search(
        query=request.query,
        sources=request.sources,
        limit=request.limit,
    )
    return PapersResponse(papers=papers)


@router.post("/latest", response_model=PapersResponse)
async def latest_papers(request: LatestPapersRequest) -> PapersResponse:
    papers = await get_discovery_service().latest(
        sources=request.sources,
        limit=request.limit,
        category=request.category,
    )
    return PapersResponse(papers=papers)


@router.post("/ingest", response_model=IngestionResponse)
async def ingest_papers(request: IngestPapersRequest) -> IngestionResponse:
    job = await get_ingestion_pipeline().ingest(request)
    return IngestionResponse(job_id=job.job_id, status=job.status, papers=job.papers)


@router.get("/ingest/{job_id}", response_model=IngestionStatusResponse)
async def get_ingestion_status(job_id: str) -> IngestionStatusResponse:
    job = get_status_store().get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Ingestion job not found.")
    return IngestionStatusResponse(job_id=job.job_id, status=job.status, papers=job.papers, error=job.error)
