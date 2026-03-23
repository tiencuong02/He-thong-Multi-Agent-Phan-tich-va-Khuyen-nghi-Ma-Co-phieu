import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

class MongoDB:
    client: AsyncIOMotorClient = None
    db = None

db_instance = MongoDB()

async def connect_to_mongo():
    logger.info("Connecting to MongoDB...")
    try:
        # settings.MONGO_URI should be defined in app.core.config
        db_instance.client = AsyncIOMotorClient(
            settings.MONGO_URI, 
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000
        )
        db_instance.db = db_instance.client.get_default_database()
        
        # Ensure indexes with timeout
        await asyncio.wait_for(db_instance.db["reports"].create_index("ticker"), timeout=5.0)
        await asyncio.wait_for(db_instance.db["reports"].create_index([("created_at", -1)]), timeout=5.0)
        
        logger.info(f"Connected to MongoDB at {settings.MONGO_URI}")
    except Exception as e:
        logger.error(f"Could not connect to MongoDB: {e}")
        db_instance.client = None
        db_instance.db = None

async def close_mongo_connection():
    logger.info("Closing MongoDB connection...")
    if db_instance.client:
        db_instance.client.close()
        logger.info("Closed MongoDB connection")

def get_db():
    return db_instance.db
