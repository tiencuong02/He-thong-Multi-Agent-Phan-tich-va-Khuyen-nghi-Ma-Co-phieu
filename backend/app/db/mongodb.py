import os
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("MONGO_DB_NAME", "stock_analysis")

class MongoDB:
    client: AsyncIOMotorClient = None
    db = None

db_instance = MongoDB()

async def connect_to_mongo():
    try:
        db_instance.client = AsyncIOMotorClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        db_instance.db = db_instance.client[DATABASE_NAME]
        # Verify connection - disabled for local UI testing
        # await db_instance.client.admin.command('ping')
        # print(f"Connected to MongoDB at {MONGO_URI}")
    except Exception as e:
        print(f"Could not connect to MongoDB: {e}")
        db_instance.client = None
        db_instance.db = None

async def close_mongo_connection():
    if db_instance.client:
        db_instance.client.close()
        print("Closed MongoDB connection")

def get_db():
    return db_instance.db
