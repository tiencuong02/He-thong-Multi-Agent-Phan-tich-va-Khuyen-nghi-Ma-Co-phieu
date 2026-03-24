from typing import List, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.models.quote import Quote, QuoteCreate, QuoteUpdate, QuoteLog, QuoteContext
from bson import ObjectId
from datetime import datetime

class QuoteRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.quotes_collection = db["quotes"]
        self.logs_collection = db["quote_logs"]

    async def get_all(self) -> List[Quote]:
        cursor = self.quotes_collection.find()
        quotes = []
        async for doc in cursor:
            doc["id"] = str(doc.pop("_id"))
            quotes.append(Quote(**doc))
        return quotes

    async def get_by_id(self, quote_id: str) -> Optional[Quote]:
        doc = await self.quotes_collection.find_one({"_id": ObjectId(quote_id)})
        if doc:
            doc["id"] = str(doc.pop("_id"))
            return Quote(**doc)
        return None

    async def get_by_context(self, context: QuoteContext) -> List[Quote]:
        cursor = self.quotes_collection.find({"context": context})
        quotes = []
        async for doc in cursor:
            doc["id"] = str(doc.pop("_id"))
            quotes.append(Quote(**doc))
        return quotes

    async def create(self, quote_in: QuoteCreate) -> Quote:
        quote_dict = quote_in.model_dump()
        quote_dict["created_at"] = datetime.utcnow()
        result = await self.quotes_collection.insert_one(quote_dict)
        quote_dict["id"] = str(result.inserted_id)
        return Quote(**quote_dict)

    async def update(self, quote_id: str, quote_in: QuoteUpdate) -> Optional[Quote]:
        update_data = {k: v for k, v in quote_in.model_dump().items() if v is not None}
        if not update_data:
            return await self.get_by_id(quote_id)
        
        await self.quotes_collection.update_one(
            {"_id": ObjectId(quote_id)},
            {"$set": update_data}
        )
        return await self.get_by_id(quote_id)

    async def delete(self, quote_id: str) -> bool:
        result = await self.quotes_collection.delete_one({"_id": ObjectId(quote_id)})
        return result.deleted_count > 0

    async def log_quote_shown(self, log: QuoteLog):
        await self.logs_collection.insert_one(log.model_dump())

    async def get_stats(self) -> List[dict]:
        pipeline = [
            {"$group": {"_id": "$quote_id", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        cursor = self.logs_collection.aggregate(pipeline)
        stats = []
        async for doc in cursor:
            quote = await self.get_by_id(doc["_id"])
            if quote:
                stats.append({
                    "quote_id": doc["_id"],
                    "content": quote.content,
                    "author": quote.author,
                    "count": doc["count"]
                })
        return stats

    async def get_user_stats(self) -> List[dict]:
        pipeline = [
            {"$group": {
                "_id": "$user_id", 
                "total_quotes": {"$sum": 1},
                "quotes": {"$push": "$quote_id"}
            }},
            {"$sort": {"total_quotes": -1}}
        ]
        cursor = self.logs_collection.aggregate(pipeline)
        stats = []
        async for doc in cursor:
            # Simple most used calculation
            quote_counts = {}
            for q_id in doc["quotes"]:
                quote_counts[q_id] = quote_counts.get(q_id, 0) + 1
            
            most_used_id = max(quote_counts, key=quote_counts.get) if quote_counts else None
            most_used_quote = await self.get_by_id(most_used_id) if most_used_id else None
            
            stats.append({
                "user_id": doc["_id"],
                "total_shown": doc["total_quotes"],
                "most_used_content": most_used_quote.content if most_used_quote else "N/A"
            })
        return stats
