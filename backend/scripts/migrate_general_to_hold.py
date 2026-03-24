import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os

# Assuming MONGO_URI is available or using default
MONGO_URI = "mongodb://localhost:27017"
DB_NAME = "stockdb"

async def migrate():
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]
    
    # Update Quotes
    result = await db.quotes.update_many(
        {"context": "GENERAL"},
        {"$set": {"context": "HOLD"}}
    )
    print(f"Updated {result.modified_count} quotes from GENERAL to HOLD.")
    
    # Update Quote Logs
    result_logs = await db.quote_logs.update_many(
        {"context": "GENERAL"},
        {"$set": {"context": "HOLD"}}
    )
    print(f"Updated {result_logs.modified_count} quote logs from GENERAL to HOLD.")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(migrate())
