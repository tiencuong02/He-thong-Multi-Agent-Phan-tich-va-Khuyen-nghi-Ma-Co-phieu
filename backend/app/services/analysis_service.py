import uuid
import logging
from typing import List, Optional, Any

from app.models.stock import AnalysisResult, JobState, JobStatusResponse
from app.repositories.report_repository import ReportRepository
from app.repositories.job_repository import JobRepository
from app.api.kafka_producer import KafkaProducerService

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

    async def initiate_analysis(self, ticker: str, user_id: Optional[str] = None) -> str:
        ticker = ticker.upper()
        job_id = str(uuid.uuid4())
        
        # Initial Job State
        job_state = JobState(job_id=job_id, status="pending", ticker=ticker)
        await self.job_repo.save_job(job_id, job_state)
        
        # Try Kafka
        message = {"job_id": job_id, "ticker": ticker, "user_id": user_id}
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

    async def get_history(self, user_id: Optional[str] = None) -> List[AnalysisResult]:
        return await self.report_repo.get_recent_reports(user_id=user_id)

    async def get_featured_stock(self, investment_style: str) -> dict:
        """
        Get a featured stock recommendation based on user investment style.
        """
        if investment_style == "short_term":
            ticker = "NVDA"
            reason = "có biến động giá cao (Volatility) + thanh khoản cực tốt, phù hợp tối ưu lợi nhuận trong vài ngày."
        else:
            ticker = "FPT"
            reason = "có nền tảng cơ bản vững chắc và đang trong xu hướng tăng trưởng bền vững (Long-term trend)."

        # Try to get the latest real report for this ticker
        reports = await self.report_repo.get_recent_reports(ticker=ticker)
        if reports:
            latest = reports[0]
            return {
                "ticker": ticker,
                "recommendation": latest.recommendation,
                "price": latest.price,
                "reason": reason,
                "strategy": latest.investment_strategy
            }
        
        # Fallback if no real report yet
        return {
            "ticker": ticker,
            "recommendation": "BUY",
            "price": 0,
            "reason": reason,
            "strategy": "Cân nhắc tích lũy dần tại các nhịp điều chỉnh."
        }

    async def process_analysis_sync(self, job_id: str, ticker: str, user_id: Optional[str] = None):
        """Used for synchronous fallback or internal worker calls"""
        try:
            # Update state to processing
            state = await self.job_repo.get_job(job_id)
            if state:
                state.status = "processing"
                await self.job_repo.save_job(job_id, state)

            from app.agents.crew import run_analysis
            # Core Agent Pipeline
            result_dict = await run_analysis(ticker)
            
            if result_dict.get("status") == "error":
                raise Exception(result_dict.get("error"))

            # Normalize agent output: agent returns 'symbol', model needs 'ticker'
            if "symbol" in result_dict and "ticker" not in result_dict:
                result_dict["ticker"] = result_dict.pop("symbol")

            result = AnalysisResult(**result_dict)
            result.user_id = user_id
            
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
