import asyncio
import motor.motor_asyncio
import os
from dotenv import load_dotenv
from bson import ObjectId

load_dotenv(".env")

async def check():
    uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/stockdb")
    client = motor.motor_asyncio.AsyncIOMotorClient(uri)
    db = client.get_default_database()
    
    print("--- QUOTES ---")
    async for q in db["quotes"].find():
        print(f"ID: {q['_id']}, Context: {q.get('context')}")
        
    print("\n--- LOGS ---")
    async for l in db["quote_logs"].find().limit(5):
        print(f"User: {l.get('user_id')}, QuoteID: {l.get('quote_id')}, Type: {type(l.get('quote_id'))}")

    print("\n--- AGGREGATION TEST ---")
    pipeline = [
        {"$group": {"_id": "$quote_id", "count": {"$sum": 1}}},
    ]
    cursor = db["quote_logs"].aggregate(pipeline)
    async for doc in cursor:
        print(f"Aggregated QuoteID: {doc['_id']}, Count: {doc['count']}")
        # Check if this ID exists in quotes
        exists = await db["quotes"].find_one({"_id": ObjectId(doc["_id"]) if isinstance(doc["_id"], str) else doc["_id"]})
        print(f"Exists in quotes: {exists is not None}")

    client.close()

if __name__ == "__main__":
    asyncio.run(check())
