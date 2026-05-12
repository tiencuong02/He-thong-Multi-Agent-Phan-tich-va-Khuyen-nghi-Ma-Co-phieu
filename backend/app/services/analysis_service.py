import uuid
import logging
from typing import List, Optional, Any

from app.models.stock import AnalysisResult, JobState, JobStatusResponse, AgentProgressStep
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

    async def initiate_analysis(self, ticker: str, user_id: Optional[str] = None) -> tuple[str, bool]:
        """
        Returns (job_id, kafka_published).
        kafka_published=True  → Worker sẽ consume và xử lý qua Kafka pipeline.
        kafka_published=False → Caller phải tự chạy BackgroundTask fallback.
        """
        ticker = ticker.upper()
        job_id = str(uuid.uuid4())

        # Initial Job State
        job_state = JobState(job_id=job_id, status="pending", ticker=ticker)
        await self.job_repo.save_job(job_id, job_state)

        # Publish to Kafka — Worker sẽ consume và xử lý
        message = {"job_id": job_id, "ticker": ticker, "user_id": user_id}
        published = await self.kafka_producer.publish_message(message)

        if published:
            logger.info(f"Job {job_id} published to Kafka — Worker will process {ticker}.")
        else:
            logger.warning(f"Kafka unavailable for {ticker} — BackgroundTask fallback required.")

        return job_id, published

    async def get_job_status(self, job_id: str, user_id: Optional[str] = None) -> Optional[JobStatusResponse]:
        state = await self.job_repo.get_job(job_id)
        if not state:
            return None
        
        # Safety net: nếu job completed nhưng report chưa có trong MongoDB → lưu lại
        if state.status == "completed" and state.result and user_id:
            try:
                existing = await self.report_repo.get_recent_reports(limit=1, user_id=user_id, ticker=state.result.ticker)
                # Chỉ lưu nếu chưa có report nào cho ticker này trong vòng 5 phút gần nhất
                from datetime import datetime, timedelta
                should_save = True
                if existing:
                    time_diff = datetime.utcnow() - existing[0].created_at
                    if time_diff < timedelta(minutes=5):
                        should_save = False
                
                if should_save:
                    state.result.user_id = user_id
                    await self.report_repo.save_report(state.result)
                    logger.info(f"Safety net: saved report for {state.result.ticker} to MongoDB (job {job_id})")
            except Exception as e:
                logger.warning(f"Safety net save failed for job {job_id}: {e}")

            # Fetch quote if needed
            if not state.result.quote and self.quote_service:
                try:
                    from app.models.quote import QuoteContext
                    context = QuoteContext.HOLD
                    rec = state.result.recommendation.upper()
                    if "BUY" in rec:
                        context = QuoteContext.BUY
                    elif "SELL" in rec:
                        context = QuoteContext.SELL
                    state.result.quote = await self.quote_service.get_random_quote(user_id, context)
                except Exception as e:
                    logger.warning(f"Quote fetch failed for job {job_id}: {e}")
        
        return JobStatusResponse(
            job_id=state.job_id,
            status=state.status,
            result=state.result,
            error=state.error,
            agent_steps=state.agent_steps,
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
            # Update state to processing + khởi tạo agent_steps
            state = await self.job_repo.get_job(job_id)
            if state:
                state.status = "processing"
                state.agent_steps = [
                    AgentProgressStep(name="Market Researcher",  status="pending"),
                    AgentProgressStep(name="Financial Analyst",  status="pending"),
                    AgentProgressStep(name="Investment Advisor", status="pending"),
                ]
                await self.job_repo.save_job(job_id, state)

            # Callback cập nhật từng bước agent vào Redis
            async def progress_cb(name: str, status: str, detail: str = ""):
                s = await self.job_repo.get_job(job_id)
                if s:
                    for step in s.agent_steps:
                        if step.name == name:
                            step.status = status
                            step.detail = detail
                            break
                    await self.job_repo.save_job(job_id, s)

            from app.agents.graph import run_analysis
            # Core Agent Pipeline với real-time progress
            result_dict = await run_analysis(ticker, progress_cb=progress_cb)
            
            if result_dict is None:
                raise Exception(f"Analysis pipeline returned None for ticker {ticker}. Check API quotas or symbol validity.")

            if result_dict.get("status") == "error":
                raise Exception(result_dict.get("error"))

            # Normalize agent output: agent returns 'symbol', model needs 'ticker'
            if "symbol" in result_dict and "ticker" not in result_dict:
                result_dict["ticker"] = result_dict.pop("symbol")

            result = AnalysisResult(**result_dict)
            result.user_id = user_id
            
            # Save to MongoDB via repo
            try:
                await self.report_repo.save_report(result)
                logger.info(f"Report saved to MongoDB for {ticker} (job {job_id})")
            except Exception as save_err:
                logger.error(f"MongoDB save failed for {ticker} (job {job_id}): {save_err}")
                # Continue to update Redis so frontend still gets result
            
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
