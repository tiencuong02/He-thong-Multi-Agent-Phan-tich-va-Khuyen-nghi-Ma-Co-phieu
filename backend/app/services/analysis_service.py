import uuid
import logging
from typing import List, Optional, Any

from app.models.stock import AnalysisResult, JobState, JobStatusResponse
from app.repositories.report_repository import ReportRepository
from app.repositories.job_repository import JobRepository
from app.api.kafka_producer import KafkaProducerService
from app.agents.crew import run_analysis

logger = logging.getLogger(__name__)

class AnalysisService:
    def __init__(
        self, 
        report_repo: ReportRepository, 
        job_repo: JobRepository,
        kafka_producer: KafkaProducerService,
        quote_service: Optional[Any] = None # Avoid circular import
    ):
        self.report_repo = report_repo
        self.job_repo = job_repo
        self.kafka_producer = kafka_producer
        self.quote_service = quote_service

    async def initiate_analysis(self, ticker: str) -> str:
        ticker = ticker.upper()
        job_id = str(uuid.uuid4())
        
        # Initial Job State
        job_state = JobState(job_id=job_id, status="pending", ticker=ticker)
        await self.job_repo.save_job(job_id, job_state)
        
        # Try Kafka
        message = {"job_id": job_id, "ticker": ticker}
        published = await self.kafka_producer.publish_message(message)
        
        if not published:
            logger.warning(f"Kafka unavailable. Falling back to background task for {ticker}")
            # The API level can handle the background task trigger if needed,
            # or the service can do it. For simpler DI, we'll return the job_id
            # and let the endpoint decide on the fallback execution.
        
        return job_id

    async def get_job_status(self, job_id: str, user_id: Optional[str] = None) -> Optional[JobStatusResponse]:
        state = await self.job_repo.get_job(job_id)
        if not state:
            return None
        
        # If completed and we have a user_id, and no quote yet, fetch one
        if state.status == "completed" and state.result and not state.result.quote and user_id and self.quote_service:
            from app.models.quote import QuoteContext
            context = QuoteContext.GENERAL
            rec = state.result.recommendation.upper()
            if "BUY" in rec:
                context = QuoteContext.BUY
            elif "SELL" in rec:
                context = QuoteContext.SELL
            
            state.result.quote = await self.quote_service.get_random_quote(user_id, context)
            # We don't necessarily need to save it back to the report repo here, 
            # as it's a dynamic "shown" quote, but logging is handled by quote_service.
        
        return JobStatusResponse(
            job_id=state.job_id, 
            status=state.status, 
            result=state.result, 
            error=state.error
        )

    async def get_history(self) -> List[AnalysisResult]:
        return await self.report_repo.get_recent_reports()

    async def process_analysis_sync(self, job_id: str, ticker: str):
        """Used for synchronous fallback or internal worker calls"""
        try:
            # Update state to processing
            state = await self.job_repo.get_job(job_id)
            if state:
                state.status = "processing"
                await self.job_repo.save_job(job_id, state)

            # Core Agent Pipeline
            result_dict = await run_analysis(ticker)
            
            if result_dict.get("status") == "error":
                raise Exception(result_dict.get("error"))

            # Normalize agent output: agent returns 'symbol', model needs 'ticker'
            if "symbol" in result_dict and "ticker" not in result_dict:
                result_dict["ticker"] = result_dict.pop("symbol")

            result = AnalysisResult(**result_dict)
            
            # Save to MongoDB via repo
            await self.report_repo.save_report(result)
            
            # Update Redis via repo
            if state:
                state.status = "completed"
                state.result = result
                await self.job_repo.save_job(job_id, state)
                
        except Exception as e:
            logger.error(f"Service processing failed for {job_id}: {e}")
            state = await self.job_repo.get_job(job_id)
            if state:
                state.status = "failed"
                state.error = str(e)
                await self.job_repo.save_job(job_id, state)
