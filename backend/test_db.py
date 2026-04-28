import asyncio
import pprint
from dotenv import load_dotenv
load_dotenv()
from app.db.mongodb import init_db, get_db

async def main():
    await init_db()
    db = get_db()
    cursor = db["knowledge_base"].find()
    docs = await cursor.to_list(length=10)
    pprint.pprint(docs)

asyncio.run(main())
