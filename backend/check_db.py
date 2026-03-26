import asyncio
import motor.motor_asyncio
import os
from dotenv import load_dotenv

load_dotenv()

async def check():
    uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/stockdb")
    client = motor.motor_asyncio.AsyncIOMotorClient(uri)
    db = client.get_default_database()
    
    # Check reports
    count = await db["reports"].count_documents({})
    print(f"Total reports: {count}")
    
    cursor = db["reports"].find().limit(5)
    async for doc in cursor:
        print(f"\nID: {doc['_id']}")
        print(f"Ticker: {doc.get('ticker')}")
        print(f"User ID: {doc.get('user_id')}")
        print(f"Created At: {doc.get('created_at')}")
    
    # Check users
    user_count = await db["users"].count_documents({})
    print(f"\nTotal users: {user_count}")
    async for user in db["users"].find():
        print(f"User: {user.get('username')}, ID: {user.get('_id')}")

    client.close()

if __name__ == "__main__":
    asyncio.run(check())
