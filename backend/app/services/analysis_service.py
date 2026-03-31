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
            context = QuoteContext.HOLD
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

    async def get_featured_stock(self, investment_style: str) -> Optional[dict]:
        """
        Get a featured stock recommendation based on user investment style.
        """
        # Lấy tối đa 20 báo cáo gần nhất từ DB
        reports = await self.report_repo.get_recent_reports(limit=20)
        
        if not reports:
            return None
            
        # 1. Deduplicate by ticker: only keep the LATEST report for each ticker
        latest_reports_by_ticker = {}
        for r in reports:
            if r.ticker not in latest_reports_by_ticker:
                latest_reports_by_ticker[r.ticker] = r
        
        # 2. Get candidates that are actually BUY in their latest status
        buy_candidates = [
            r for r in latest_reports_by_ticker.values() 
            if r.recommendation and r.recommendation.upper() in ["BUY", "STRONG BUY"]
        ]
        
        if not buy_candidates:
            return None
            
        # 3. Ưu tiên chọn mã phù hợp với phong cách đầu tư
        filtered_reports = []
        if investment_style == "short_term":
            # Ưu tiên lướt sóng
            keywords = ["lướt sóng", "ngắn hạn", "trading", "sóng", "volatility", "biến động"]
            filtered_reports = [r for r in buy_candidates if any(k in (r.investment_strategy or "").lower() for k in keywords)]
        else:
            # Ưu tiên tích sản/dài hạn
            keywords = ["tích sản", "dài hạn", "giữ", "giá trị", "bền vững", "long-term"]
            filtered_reports = [r for r in buy_candidates if any(k in (r.investment_strategy or "").lower() for k in keywords)]

        # Nếu có mã khớp phong cách thì lấy mã mới nhất, nếu không lấy mã mới nhất bất kỳ trong danh mục BUY
        featured = filtered_reports[0] if filtered_reports else buy_candidates[0]
        
        # Lấy câu đầu tiên của investment_strategy để làm lý do (reason) ngắn gọn
        strategy = featured.investment_strategy or ""
        reason = strategy.split('.')[0] + "." if strategy else "có những tín hiệu tích cực từ mô hình AI đa tác nhân."
        
        return {
            "ticker": featured.ticker,
            "recommendation": featured.recommendation.upper(),
            "price": featured.price,
            "reason": reason,
            "strategy": featured.investment_strategy
        }

    async def get_admin_stats(self) -> dict:
        """Fetch statistics for admin overview"""
        ticker_stats = await self.report_repo.get_ticker_stats()
        recommendation_stats = await self.report_repo.get_recommendation_stats()
        return {
            "top_tickers": ticker_stats,
            "recommendations": recommendation_stats
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
