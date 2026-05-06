import json
import logging
from typing import Optional, Any, List, Dict
from app.db.redis import get_redis

logger = logging.getLogger(__name__)

# TTL configuration (in seconds)
TTL_SETTINGS = {
    "price":        10,
    "history":      600,   # 10m
    "news":         900,   # 15m
    "ai_result":    180,   # 3m
    "job":          3600,  # 1h
    "rag_response": 7200,  # 2h — chatbot RAG answers
    "conversation": 7200,  # 2h — per-session conversation memory
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


class ConversationMemory:
    """Server-side conversation history per session, backed by Redis.

    Stores turns as a Redis list so the chatbot remembers previous exchanges
    without requiring the client to resend the full history on each request.

    Key: conv:{session_id}
    Each element: JSON {"role": "user"|"assistant", "content": "..."}
    """

    TTL = TTL_SETTINGS["conversation"]
    MAX_TURNS = 10       # keep at most 10 turns (20 messages)
    TRIM_LENGTH = 500    # trim long assistant messages before storing

    @staticmethod
    def _key(session_id: str) -> str:
        return f"conv:{session_id}"

    @staticmethod
    async def load(session_id: str, max_turns: int = 8) -> List[Dict]:
        """Return last max_turns turns as list of {role, content} dicts."""
        redis_client = get_redis()
        if not redis_client or not session_id:
            return []
        key = ConversationMemory._key(session_id)
        try:
            raw = await redis_client.lrange(key, -(max_turns * 2), -1)
            return [json.loads(item) for item in raw]
        except Exception as e:
            logger.warning(f"ConversationMemory.load failed session={session_id}: {e}")
            return []

    @staticmethod
    async def save_turn(session_id: str, user_msg: str, assistant_msg: str) -> None:
        """Append user+assistant turn, keep last MAX_TURNS, reset TTL."""
        redis_client = get_redis()
        if not redis_client or not session_id:
            return
        key = ConversationMemory._key(session_id)
        trimmed = (
            assistant_msg[: ConversationMemory.TRIM_LENGTH] + "…"
            if len(assistant_msg) > ConversationMemory.TRIM_LENGTH
            else assistant_msg
        )
        try:
            pipe = redis_client.pipeline()
            pipe.rpush(key, json.dumps({"role": "user",      "content": user_msg}))
            pipe.rpush(key, json.dumps({"role": "assistant", "content": trimmed}))
            pipe.ltrim(key, -(ConversationMemory.MAX_TURNS * 2), -1)
            pipe.expire(key, ConversationMemory.TTL)
            await pipe.execute()
        except Exception as e:
            logger.warning(f"ConversationMemory.save_turn failed session={session_id}: {e}")

    @staticmethod
    async def clear(session_id: str) -> None:
        """Delete the entire conversation history for a session."""
        redis_client = get_redis()
        if not redis_client or not session_id:
            return
        try:
            await redis_client.delete(ConversationMemory._key(session_id))
        except Exception as e:
            logger.warning(f"ConversationMemory.clear failed session={session_id}: {e}")
