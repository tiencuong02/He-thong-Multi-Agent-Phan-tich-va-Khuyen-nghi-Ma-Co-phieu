import json
from typing import Optional, Any
from app.db.redis import get_redis

# TTL configuration (in seconds)
TTL_SETTINGS = {
    "price": 10,
    "history": 600,  # 10m
    "news": 900,     # 15m
    "ai_result": 180, # 3m
}

class CacheService:
    @staticmethod
    async def get(key_type: str, identifier: str) -> Optional[Any]:
        """Get parsed JSON data from cache"""
        redis_client = get_redis()
        if not redis_client:
            return None

        key = f"{key_type}:{identifier}"
        try:
            cached_data = await redis_client.get(key)
            if cached_data:
                return json.loads(cached_data)
            return None
        except Exception as e:
            print(f"[ERROR] Cache get failed for {key}: {e}")
            return None

    @staticmethod
    async def set(key_type: str, identifier: str, data: Any) -> bool:
        """Set data to cache with specific TTLs based on key type"""
        redis_client = get_redis()
        if not redis_client:
            return False

        key = f"{key_type}:{identifier}"
        ttl = TTL_SETTINGS.get(key_type, 300) # Default TTL 5 mins

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
            
        key = f"{key_type}:{identifier}"
        try:
            await redis_client.delete(key)
            return True
        except Exception as e:
            print(f"[ERROR] Cache delete failed for {key}: {e}")
            return False
