import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends

from app.db.mongodb import get_db
from app.db.redis import redis_instance
from app.api.kafka_producer import KafkaProducerService
from app.models.stock import AnalysisResult, JobStatusResponse
from app.repositories.report_repository import ReportRepository
from app.repositories.job_repository import JobRepository
from app.services.analysis_service import AnalysisService

logger = logging.getLogger(__name__)
router = APIRouter()

# ── Dependency Injection ──────────────────────────────────────────

def get_analysis_service():
    db = get_db()
    if db is None:
        raise HTTPException(status_code=500, detail="Database connection not available")
    
    report_repo = ReportRepository(db)
    job_repo = JobRepository() # Uses redis internally
    kafka_producer = KafkaProducerService()
    
    return AnalysisService(report_repo, job_repo, kafka_producer)


# ── API Endpoints ──────────────────────────────────────────────────

@router.post("/analyze/{ticker}", response_model=JobStatusResponse)
async def analyze_stock(
    ticker: str, 
    background_tasks: BackgroundTasks,
    service: AnalysisService = Depends(get_analysis_service)
):
    """
    Initiate stock analysis for a given ticker.
    """
    ticker = ticker.upper()
    logger.info(f"FAANG API request: analyze {ticker}")
    
    try:
        job_id = await service.initiate_analysis(ticker)
        
        # We always queue a background task as a robust fallback.
        # If Kafka picks it up first, the Redis state will handle idempotency/completion.
        background_tasks.add_task(service.process_analysis_sync, job_id, ticker)
        
        return JobStatusResponse(job_id=job_id, status="pending")
        
    except Exception as e:
        logger.error(f"Failed to initiate analysis for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analyze/status/{job_id}", response_model=JobStatusResponse)
async def get_analysis_status(
    job_id: str,
    service: AnalysisService = Depends(get_analysis_service)
):
    """
    Get the current status of an analysis job.
    """
    status = await service.get_job_status(job_id)
    if not status:
        raise HTTPException(status_code=404, detail="Job not found")
    return status


@router.get("/history", response_model=List[AnalysisResult])
async def get_analysis_history(
    service: AnalysisService = Depends(get_analysis_service)
):
    """
    Fetch the list of most recent analysis reports.
    """
    return await service.get_history()


@router.delete("/history")
async def delete_history(
    service: AnalysisService = Depends(get_analysis_service)
):
    """
    Clear historical data.
    """
    await service.report_repo.delete_all()
    return {"message": "History cleared successfully"}
