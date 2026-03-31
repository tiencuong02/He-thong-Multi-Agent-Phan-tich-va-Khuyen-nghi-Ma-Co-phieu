import asyncio
import motor.motor_asyncio
import os
from dotenv import load_dotenv

load_dotenv(".env")

async def check():
    uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/stockdb")
    client = motor.motor_asyncio.AsyncIOMotorClient(uri)
    db = client.get_default_database()
    
    # Check quotes
    quote_count = await db["quotes"].count_documents({})
    print(f"Total quotes in 'quotes' collection: {quote_count}")
    
    # Check logs
    log_count = await db["quote_logs"].count_documents({})
    print(f"Total logs in 'quote_logs' collection: {log_count}")
    
    # Check distinct users in logs
    active_users = await db["quote_logs"].distinct("user_id")
    print(f"Active users (distinct in logs): {len(active_users)}")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(check())
