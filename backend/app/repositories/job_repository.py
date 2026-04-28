from typing import Optional, Dict
import json
import logging
from app.db.redis import redis_instance
from app.models.stock import JobState

logger = logging.getLogger(__name__)

# In-memory fallback khi Redis không khả dụng (dev/local mode)
# Key: "job:{job_id}" → JSON string
_memory_store: Dict[str, str] = {}


class JobRepository:
    """
    Handles job state persistence.
    Primary: Redis (production)
    Fallback: in-memory dict (dev mode khi Redis chưa chạy)
    """

    @staticmethod
    async def get_job(job_id: str) -> Optional[JobState]:
        key = f"job:{job_id}"
        try:
            if redis_instance.client is not None:
                data = await redis_instance.client.get(key)
            else:
                data = _memory_store.get(key)

            if data:
                return JobState(**json.loads(data))
        except Exception as e:
            logger.warning(f"JobRepository.get_job failed: {e}")
            # Fallback về memory store nếu Redis lỗi giữa chừng
            data = _memory_store.get(key)
            if data:
                return JobState(**json.loads(data))
        return None

    @staticmethod
    async def save_job(job_id: str, state: JobState, expire: int = 3600):
        key = f"job:{job_id}"
        payload = state.json()
        try:
            if redis_instance.client is not None:
                await redis_instance.client.setex(key, expire, payload)
            else:
                logger.warning(
                    f"Redis unavailable — saving job {job_id} to in-memory store (dev mode). "
                    "Start Redis for production: docker-compose up -d redis"
                )
                _memory_store[key] = payload
                # Giới hạn memory store để tránh leak (giữ tối đa 500 jobs)
                if len(_memory_store) > 500:
                    oldest = next(iter(_memory_store))
                    del _memory_store[oldest]
        except Exception as e:
            logger.error(f"JobRepository.save_job Redis error: {e} — falling back to memory")
            _memory_store[key] = payload
