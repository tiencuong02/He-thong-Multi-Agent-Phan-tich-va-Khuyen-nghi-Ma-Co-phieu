
import asyncio
import os
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

async def check():
    load_dotenv()
    uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/stockdb")
    client = AsyncIOMotorClient(uri)
    db = client.get_database()
    
    docs = await db["knowledge_base"].find({"status": "processing"}).to_list(10)
    if not docs:
        print("No documents are currently in 'processing' status.")
    else:
        for d in docs:
            print(f"Document: {d.get('filename')} | Ticker: {d.get('ticker')} | Chunks: {d.get('chunks_count')} | Status: {d.get('status')}")

if __name__ == "__main__":
    asyncio.run(check())
