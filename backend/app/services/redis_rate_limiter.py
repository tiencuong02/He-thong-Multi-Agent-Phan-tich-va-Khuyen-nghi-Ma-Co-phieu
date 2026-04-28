"""
Rate Limiter — sliding window algorithm.
  - Redis backend: dùng khi có Redis (multi-process/pod safe)
  - InMemory fallback: dùng khi Redis down (single-process only)

Cả hai implement cùng interface async is_allowed() / retry_after().
"""
import time
import logging
from collections import defaultdict
from typing import Optional

logger = logging.getLogger(__name__)


class RedisRateLimiter:
    """
    Sliding window rate limiter dùng Redis Sorted Set.
    Hoạt động đúng qua nhiều Uvicorn workers hoặc Docker pods.

    Algorithm:
      key = sorted set, member = timestamp (str), score = timestamp (float)
      1. ZREMRANGEBYSCORE key 0 (now - window)   → xóa entries cũ
      2. ZCARD key                                → đếm requests còn lại
      3. ZADD key now:now                         → thêm request hiện tại
      4. EXPIRE key window+5                      → TTL tự cleanup
      Cho phép nếu count (trước bước 3) < max_calls.
    """

    def __init__(self, redis_client):
        self._r = redis_client

    async def is_allowed(self, key: str, max_calls: int, window_seconds: int) -> bool:
        if self._r is None:
            return True  # Redis down → fail open (không chặn user)

        now = time.time()
        cutoff = now - window_seconds
        rkey = f"rl:{key}"

        try:
            async with self._r.pipeline(transaction=True) as pipe:
                pipe.zremrangebyscore(rkey, 0, cutoff)
                pipe.zcard(rkey)
                pipe.zadd(rkey, {f"{now:.6f}": now})
                pipe.expire(rkey, window_seconds + 5)
                results = await pipe.execute()
            count_before = results[1]  # ZCARD trước khi ZADD
            return count_before < max_calls
        except Exception as e:
            logger.warning(f"RedisRateLimiter error ({key}): {e} — allowing")
            return True  # lỗi Redis → fail open

    async def retry_after(self, key: str, window_seconds: int) -> int:
        if self._r is None:
            return 0
        try:
            rkey = f"rl:{key}"
            oldest = await self._r.zrange(rkey, 0, 0, withscores=True)
            if not oldest:
                return 0
            oldest_ts = oldest[0][1]
            return max(0, int(window_seconds - (time.time() - oldest_ts)) + 1)
        except Exception:
            return 0


class InMemoryRateLimiter:
    """
    Fallback in-memory rate limiter khi Redis không khả dụng.
    Chỉ đúng trong single-process; dùng CPython GIL để list ops thread-safe.
    """

    def __init__(self):
        self._buckets: dict = defaultdict(list)

    async def is_allowed(self, key: str, max_calls: int, window_seconds: int) -> bool:
        now = time.monotonic()
        cutoff = now - window_seconds
        calls = self._buckets[key]
        # Xóa timestamps ngoài window
        while calls and calls[0] < cutoff:
            calls.pop(0)
        if len(calls) >= max_calls:
            return False
        calls.append(now)
        return True

    async def retry_after(self, key: str, window_seconds: int) -> int:
        calls = self._buckets.get(key, [])
        if not calls:
            return 0
        return max(0, int(window_seconds - (time.monotonic() - calls[0])) + 1)


def make_rate_limiter(redis_client=None):
    """
    Factory: trả về Redis limiter nếu có client, fallback về InMemory.
    Gọi từ startup sau khi Redis đã connect.
    """
    if redis_client is not None:
        logger.info("RateLimiter: using Redis backend (multi-process safe)")
        return RedisRateLimiter(redis_client)
    logger.warning("RateLimiter: Redis unavailable — using in-memory fallback")
    return InMemoryRateLimiter()
