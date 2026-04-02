import logging
from typing import List
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends

from app.db.mongodb import get_db
from app.models.stock import AnalysisResult, JobStatusResponse
from app.repositories.report_repository import ReportRepository
from app.repositories.job_repository import JobRepository
from app.services.analysis_service import AnalysisService
from . import auth
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()

# ── Dependency Injection ──────────────────────────────────────────

def get_analysis_service():
    db = get_db()
    if db is None:
        raise HTTPException(status_code=500, detail="Database connection not available")
    
    report_repo = ReportRepository(db)
    job_repo = JobRepository() # Uses redis internally
    
    from app.repositories.quote_repository import QuoteRepository
    from app.services.quote_service import QuoteService
    from app.api.kafka_producer import KafkaProducerService
    
    quote_repo = QuoteRepository(db)
    quote_service = QuoteService(quote_repo)
    kafka_producer = KafkaProducerService()
    
    return AnalysisService(report_repo, job_repo, kafka_producer, quote_service)


# ── API Endpoints ──────────────────────────────────────────────────

@router.post("/analyze/{ticker}", response_model=JobStatusResponse)
async def analyze_stock(
    ticker: str, 
    background_tasks: BackgroundTasks,
    service: AnalysisService = Depends(get_analysis_service),
    current_user: User = Depends(auth.get_current_user)
):
    """
    Initiate stock analysis for a given ticker.
    """
    ticker = ticker.upper()
    logger.info(f"FAANG API request: analyze {ticker} for user {current_user.username}")
    
    try:
        job_id = await service.initiate_analysis(ticker, user_id=current_user.id)
        background_tasks.add_task(service.process_analysis_sync, job_id, ticker, user_id=current_user.id)
        return JobStatusResponse(job_id=job_id, status="pending")
        
    except Exception as e:
        logger.error(f"Failed to initiate analysis for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analyze/status/{job_id}")
async def get_analysis_status(
    job_id: str,
    service: AnalysisService = Depends(get_analysis_service),
    current_user: User = Depends(auth.get_current_user)
):
    """
    Get the current status of an analysis job.
    """
    try:
        status = await service.get_job_status(job_id, user_id=current_user.id)
        if not status:
            raise HTTPException(status_code=404, detail="Job not found")
        return status
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/")
async def get_analysis_history(
    service: AnalysisService = Depends(get_analysis_service),
    current_user: User = Depends(auth.get_current_user)
):
    """
    Fetch the list of most recent analysis reports for the current user.
    """
    return await service.get_history(user_id=current_user.id)


@router.delete("/history")
async def delete_history(
    service: AnalysisService = Depends(get_analysis_service)
):
    """
    Clear historical data.
    """
    await service.report_repo.delete_all()
    return {"message": "History cleared successfully"}


@router.get("/stats/")
async def get_stock_stats(
    service: AnalysisService = Depends(get_analysis_service),
    admin_user: User = Depends(auth.check_admin_role)
):
    """
    Get aggregated stock analysis statistics (Admin only).
    """
    return await service.get_admin_stats()


@router.get("/featured/")
async def get_featured_stock(
    service: AnalysisService = Depends(get_analysis_service),
    current_user: User = Depends(auth.get_current_user)
):
    """
    Get a proactive stock recommendation based on user style.
    """
    return await service.get_featured_stock(current_user.investment_style)
