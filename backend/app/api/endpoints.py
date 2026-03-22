from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
import uuid
from typing import List, Optional, Dict, Any
import datetime
import asyncio
import traceback

from app.db.mongodb import get_db
from app.db.cache_service import CacheService
from app.api.kafka_producer import KafkaProducerService

router = APIRouter()

# ─── In-memory fallback store (dùng khi Redis không khả dụng) ──────────────────
_job_store: Dict[str, Dict[str, Any]] = {}

def _store_get(job_id: str) -> Optional[Dict]:
    return _job_store.get(job_id)

def _store_set(job_id: str, data: Dict):
    _job_store[job_id] = data

# ─── Pydantic Models ────────────────────────────────────────────────────────────
class AnalysisResponse(BaseModel):
    ticker: str
    risk_opportunity: str
    recommendation: str
    created_at: str

class JobCreationResponse(BaseModel):
    job_id: str
    status: str
    message: str

class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    result: Optional[AnalysisResponse] = None
    error: Optional[str] = None

# ─── Helper: lưu job vào cả Redis (nếu có) và in-memory ────────────────────────
async def save_job(job_id: str, data: Dict):
    _store_set(job_id, data)
    try:
        await CacheService.set("job", job_id, data)
    except Exception:
        pass  # Redis không có → chỉ dùng in-memory

async def get_job(job_id: str) -> Optional[Dict]:
    # Thử Redis trước
    try:
        result = await CacheService.get("job", job_id)
        if result:
            return result
    except Exception:
        pass
    # Fallback in-memory
    return _store_get(job_id)

# ─── Background task: chạy phân tích khi Kafka không có ────────────────────────
async def run_analysis_background(job_id: str, ticker: str):
    """Chạy phân tích AI trực tiếp (không qua Kafka) trong background"""
    from app.agents.crew import run_analysis

    await save_job(job_id, {"status": "processing", "ticker": ticker})
    try:
        # run_analysis is now an async function
        result_dict = await asyncio.wait_for(
            run_analysis(ticker),
            timeout=300.0  # 5 minutes max
        )

        report = {
            "ticker": ticker,
            "risk_opportunity": result_dict.get("risk_opportunity", "N/A"),
            "recommendation": result_dict.get("recommendation", "Hold"),
            "created_at": datetime.datetime.utcnow().isoformat()
        }

        # Lưu vào MongoDB
        db = get_db()
        if db is not None:
            await db["reports"].insert_one(report.copy())

        report.pop("_id", None)

        # Lưu cache Redis nếu có
        try:
            await CacheService.set("ai_result", ticker, report)
        except Exception:
            pass

        await save_job(job_id, {"status": "completed", "result": report})

    except Exception as e:
        print(f"[ERROR] Background analysis failed for {ticker}: {e}")
        traceback.print_exc()
        await save_job(job_id, {"status": "failed", "error": str(e)})

def _find_processing_job_for_ticker(ticker: str) -> Optional[str]:
    """Return an existing job_id if this ticker is already being processed, else None."""
    for jid, data in _job_store.items():
        if data.get("ticker") == ticker and data.get("status") == "processing":
            return jid
    return None


# ─── Endpoints ──────────────────────────────────────────────────────────────────
@router.post("/analyze/{ticker}", response_model=JobCreationResponse)
async def analyze_stock(ticker: str, background_tasks: BackgroundTasks):
    ticker = ticker.upper()

    # 1. Kiểm tra Redis cache trước
    try:
        cached_data = await CacheService.get("ai_result", ticker)
        if cached_data:
            job_id = str(uuid.uuid4())
            print(f"[CACHE HIT] Returning cached data for {ticker} | job_id={job_id}")
            await save_job(job_id, {"status": "completed", "result": cached_data})
            return JobCreationResponse(job_id=job_id, status="completed", message="Data loaded from cache.")
    except Exception as e:
        print(f"[WARN] Redis unavailable: {e}")

    # 2. In-flight dedup: nếu ticker đang được xử lý → trả lại job_id cũ
    existing_job_id = _find_processing_job_for_ticker(ticker)
    if existing_job_id:
        print(f"[DEDUP] ticker={ticker} already processing as job_id={existing_job_id}")
        return JobCreationResponse(job_id=existing_job_id, status="processing", message="Analysis already in progress.")

    job_id = str(uuid.uuid4())

    # 3. Thử gửi qua Kafka
    kafka_ok = False
    try:
        message = {"job_id": job_id, "ticker": ticker}
        kafka_ok = await KafkaProducerService.publish_message(message)
        if kafka_ok:
            await save_job(job_id, {"status": "processing", "ticker": ticker})
            print(f"[KAFKA] Job {job_id} published for {ticker}")
    except Exception as e:
        print(f"[WARN] Kafka error: {e}")

    # 4. Fallback: chạy phân tích trực tiếp bằng BackgroundTasks của FastAPI
    if not kafka_ok:
        await save_job(job_id, {"status": "processing", "ticker": ticker})
        background_tasks.add_task(run_analysis_background, job_id, ticker)
        print(f"[FALLBACK] Job {job_id} started as background task for {ticker}")

    return JobCreationResponse(job_id=job_id, status="processing", message="Analysis started.")


@router.get("/analyze/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    job_data = await get_job(job_id)
    if not job_data:
        raise HTTPException(status_code=404, detail="Job not found or expired.")

    return JobStatusResponse(
        job_id=job_id,
        status=job_data.get("status", "unknown"),
        result=job_data.get("result"),
        error=job_data.get("error")
    )


@router.get("/history", response_model=List[AnalysisResponse])
async def get_history(limit: int = 10):
    try:
        db = get_db()
        if db is None:
            raise HTTPException(status_code=500, detail="Database not connected")

        cursor = db["reports"].find().sort("created_at", -1).limit(limit)
        reports = await cursor.to_list(length=limit)

        for r in reports:
            r.pop("_id", None)

        return reports
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/history/{ticker}")
async def delete_history_item(ticker: str):
    """Xóa tất cả lịch sử phân tích của một mã cổ phiếu"""
    try:
        db = get_db()
        if db is None:
            raise HTTPException(status_code=500, detail="Database not connected")

        ticker = ticker.upper()
        result = await db["reports"].delete_many({"ticker": ticker})

        # Xóa cache Redis nếu có
        try:
            await CacheService.delete("ai_result", ticker)
        except Exception:
            pass

        return {"message": f"Đã xóa {result.deleted_count} bản ghi của {ticker}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/history")
async def delete_all_history():
    """Xóa toàn bộ lịch sử phân tích"""
    try:
        db = get_db()
        if db is None:
            raise HTTPException(status_code=500, detail="Database not connected")

        result = await db["reports"].delete_many({})
        return {"message": f"Đã xóa toàn bộ {result.deleted_count} bản ghi lịch sử"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
