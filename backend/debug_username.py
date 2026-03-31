import asyncio
import motor.motor_asyncio
import os
from dotenv import load_dotenv
from bson import ObjectId

load_dotenv(".env")

async def debug():
    uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/stockdb")
    client = motor.motor_asyncio.AsyncIOMotorClient(uri)
    db = client.get_default_database()
    
    print("--- USERS in db ---")
    async for u in db["users"].find():
        print(f"  _id type: {type(u['_id'])}, _id: {u['_id']}, username: {u.get('username')}")
    
    print("\n--- LOGS user_ids ---")
    async for l in db["quote_logs"].find().limit(3):
        uid = l.get("user_id")
        print(f"  user_id type: {type(uid)}, value: {uid}")
        
        # Try exact match
        found = await db["users"].find_one({"_id": ObjectId(uid)})
        print(f"  ObjectId lookup found: {found is not None}")
        
        # Also try string match
        found_str = await db["users"].find_one({"_id": uid})
        print(f"  String lookup found: {found_str is not None}")

    client.close()

if __name__ == "__main__":
    asyncio.run(debug())
