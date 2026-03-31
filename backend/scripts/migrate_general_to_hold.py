import asyncio
import motor.motor_asyncio
import os
from dotenv import load_dotenv

# Force load .env from parent directory
load_dotenv(".env")

async def migrate():
    uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/stockdb")
    print(f"Connecting to MongoDB at {uri}...")
    client = motor.motor_asyncio.AsyncIOMotorClient(uri)
    db = client.get_default_database()
    
    # 1. Update quotes collection
    print("Migrating 'quotes' collection...")
    result = await db["quotes"].update_many(
        {"context": "GENERAL"},
        {"$set": {"context": "HOLD"}}
    )
    print(f"✅ Updated {result.modified_count} quotes from GENERAL to HOLD.")
    
    # 2. Update quote_logs collection if exists
    print("Migrating 'quote_logs' collection...")
    log_result = await db["quote_logs"].update_many(
        {"context": "GENERAL"},
        {"$set": {"context": "HOLD"}}
    )
    print(f"✅ Updated {log_result.modified_count} logs from GENERAL to HOLD.")

    client.close()
    print("Migration complete!")

if __name__ == "__main__":
    asyncio.run(migrate())
