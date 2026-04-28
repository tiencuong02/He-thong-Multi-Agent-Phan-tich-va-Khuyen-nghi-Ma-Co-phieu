
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

async def check():
    uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/stockdb")
    client = AsyncIOMotorClient(uri)
    db = client.get_database()
    
    print("--- Documents in knowledge_base ---")
    cursor = db["knowledge_base"].find({})
    async for doc in cursor:
        print(f"ID: {doc.get('document_id')} | Ticker: {doc.get('ticker')} | Namespace: {doc.get('pinecone_namespace') or doc.get('namespace')} | Status: {doc.get('status')} | Filename: {doc.get('filename')}")

if __name__ == "__main__":
    asyncio.run(check())
