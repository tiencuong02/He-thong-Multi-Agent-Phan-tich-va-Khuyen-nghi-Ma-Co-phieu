from typing import Optional, Dict, Any
import json
from app.db.redis import redis_instance
from app.models.stock import JobState

class JobRepository:
    """
    Handles job state persistence in Redis.
    """
    @staticmethod
    async def get_job(job_id: str) -> Optional[JobState]:
        data = await redis_instance.client.get(f"job:{job_id}")
        if data:
            return JobState(**json.loads(data))
        return None

    @staticmethod
    async def save_job(job_id: str, state: JobState, expire: int = 3600):
        await redis_instance.client.setex(
            f"job:{job_id}",
            expire,
            state.json()
        )
