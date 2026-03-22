import json
from typing import Optional, Any
from app.db.redis import get_redis

# TTL configuration (in seconds)
TTL_SETTINGS = {
    "price": 10,
    "history": 600,  # 10m
    "news": 900,     # 15m
    "ai_result": 1800, # 30m
    "job": 3600,     # 1h for job status
}

class CacheService:
    @staticmethod
    def _format_key(key_type: str, identifier: str) -> str:
        # Tickers should always be normalized to upper case (e.g. price:AAPL)
        if key_type in ["price", "history", "news", "ai_result"]:
            identifier = str(identifier).upper()
        return f"{key_type}:{identifier}"

    @staticmethod
    async def get(key_type: str, identifier: str) -> Optional[Any]:
        """Get parsed JSON data from cache"""
        redis_client = get_redis()
        if not redis_client:
            return None

        key = CacheService._format_key(key_type, identifier)
        try:
            cached_data = await redis_client.get(key)
            if cached_data:
                return json.loads(cached_data)
            return None
        except Exception as e:
            print(f"[ERROR] Cache get failed for {key}: {e}")
            return None

    @staticmethod
    async def set(key_type: str, identifier: str, data: Any, custom_ttl: Optional[int] = None) -> bool:
        """Set data to cache with specific TTLs based on key type or per-key override"""
        redis_client = get_redis()
        if not redis_client:
            return False

        key = CacheService._format_key(key_type, identifier)
        ttl = custom_ttl if custom_ttl is not None else TTL_SETTINGS.get(key_type, 300)

        try:
            await redis_client.setex(key, ttl, json.dumps(data))
            return True
        except Exception as e:
            print(f"[ERROR] Cache set failed for {key}: {e}")
            return False

    @staticmethod
    async def delete(key_type: str, identifier: str) -> bool:
        redis_client = get_redis()
        if not redis_client:
            return False
            
        key = CacheService._format_key(key_type, identifier)
        try:
            await redis_client.delete(key)
            return True
        except Exception as e:
            print(f"[ERROR] Cache delete failed for {key}: {e}")
            return False

    # Synchronous wrappers for tools
    @staticmethod
    def get_sync(key_type: str, identifier: str) -> Optional[Any]:
        import redis
        import os
        REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
        try:
            r = redis.from_url(REDIS_URL, decode_responses=True, socket_timeout=2, socket_connect_timeout=2)
            key = CacheService._format_key(key_type, identifier)
            cached_data = r.get(key)
            r.close()
            if cached_data:
                return json.loads(cached_data)
        except Exception as e:
            print(f"[ERROR] Sync cache get failed: {e}")
        return None

    @staticmethod
    def set_sync(key_type: str, identifier: str, data: Any, custom_ttl: Optional[int] = None) -> bool:
        import redis
        import os
        REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
        try:
            r = redis.from_url(REDIS_URL, decode_responses=True, socket_timeout=2, socket_connect_timeout=2)
            key = CacheService._format_key(key_type, identifier)
            ttl = custom_ttl if custom_ttl is not None else TTL_SETTINGS.get(key_type, 300)
            r.setex(key, ttl, json.dumps(data))
            r.close()
            return True
        except Exception as e:
            print(f"[ERROR] Sync cache set failed: {e}")
        return False
