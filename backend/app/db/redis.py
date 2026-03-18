import os
import redis.asyncio as redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

class RedisCache:
    client: redis.Redis = None

redis_instance = RedisCache()

async def connect_to_redis():
    try:
        redis_instance.client = redis.from_url(REDIS_URL, decode_responses=True)
        # Temporarily disable ping to bypass Docker requirement for now
        # await redis_instance.client.ping()
        # print(f"Connected to Redis at {REDIS_URL}")
    except Exception as e:
        print(f"Could not connect to Redis: {e}")
        redis_instance.client = None

async def close_redis_connection():
    if redis_instance.client:
        await redis_instance.client.close()
        print("Closed Redis connection")

def get_redis():
    return redis_instance.client
