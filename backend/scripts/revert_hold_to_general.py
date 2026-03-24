import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URI = "mongodb://localhost:27017"
DB_NAME = "stockdb"

async def migrate():
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]
    
    # Revert Quotes
    result = await db.quotes.update_many(
        {"context": "HOLD"},
        {"$set": {"context": "GENERAL"}}
    )
    print(f"Reverted {result.modified_count} quotes from HOLD to GENERAL.")
    
    # Revert Quote Logs
    result_logs = await db.quote_logs.update_many(
        {"context": "HOLD"},
        {"$set": {"context": "GENERAL"}}
    )
    print(f"Reverted {result_logs.modified_count} quote logs from HOLD to GENERAL.")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(migrate())
