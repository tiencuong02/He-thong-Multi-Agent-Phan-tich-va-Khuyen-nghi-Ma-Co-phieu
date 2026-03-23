import os
import asyncio
import redis.asyncio as redis
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

class RedisCache:
    client: redis.Redis = None

redis_instance = RedisCache()

async def connect_to_redis():
    logger.info("Connecting to Redis...")
    try:
        redis_instance.client = redis.from_url(
            settings.REDIS_URL, 
            decode_responses=True,
            socket_timeout=5.0,
            socket_connect_timeout=5.0
        )
        await asyncio.wait_for(redis_instance.client.ping(), timeout=5.0)
        logger.info(f"Connected to Redis at {settings.REDIS_URL}")
    except Exception as e:
        logger.error(f"Could not connect to Redis: {e}")
        redis_instance.client = None

async def close_redis_connection():
    logger.info("Closing Redis connection...")
    if redis_instance.client:
        await redis_instance.client.close()
        logger.info("Closed Redis connection")

def get_redis():
    return redis_instance.client
