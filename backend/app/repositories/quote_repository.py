from typing import List, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.models.quote import Quote, QuoteCreate, QuoteUpdate, QuoteLog, QuoteContext
from bson import ObjectId
from datetime import datetime

class QuoteRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.quotes_collection = db["quotes"]
        self.logs_collection = db["quote_logs"]
        self.users_collection = db["users"]

    async def _resolve_username(self, user_id: str) -> str:
        """Lookup the latest username from user_id. Returns user_id prefix if not found."""
        try:
            user = await self.users_collection.find_one({"_id": ObjectId(user_id)})
            if user:
                return user.get("username", user_id[:8])
        except Exception:
            pass
        return user_id[:8] + "..."  # fallback: first 8 chars of ID

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
            # Aggregate returns _id from $group, which is quote_id string or ObjectId
            q_id = doc["_id"]
            quote = await self.get_by_id(q_id)
            if quote:
                stats.append({
                    "quote_id": str(q_id),
                    "content": quote.content,
                    "author": quote.author,
                    "count": doc["count"]
                })
        return stats

    async def get_admin_summary(self) -> dict:
        total_quotes = await self.quotes_collection.count_documents({})
        total_views = await self.logs_collection.count_documents({})
        
        # Count quotes by context
        pipeline = [
            {"$group": {"_id": "$context", "count": {"$sum": 1}}}
        ]
        context_cursor = self.quotes_collection.aggregate(pipeline)
        by_context = {}
        async for doc in context_cursor:
            # MongoDB might store context as string
            ctx = doc["_id"]
            by_context[ctx] = doc["count"]
            
        detailed = await self.get_stats()
        
        return {
            "total_quotes": total_quotes,
            "total_views": total_views,
            "by_context": by_context,
            "detailed": detailed
        }

    async def get_recent_logs(self, limit: int = 20, skip: int = 0, user_id: str = None) -> list:
        """Fetch individual log entries, optionally filtered by user_id, with pagination."""
        query = {}
        if user_id:
            query["user_id"] = user_id
        cursor = self.logs_collection.find(query).sort("timestamp", -1).skip(skip).limit(limit)
        result = []
        async for doc in cursor:
            username = await self._resolve_username(doc.get("user_id", ""))
            ts = doc.get("timestamp")
            result.append({
                "username": username,
                "user_id": doc.get("user_id", ""),
                "context": doc.get("context", ""),
                "timestamp": ts.isoformat() if ts else None,
            })
        return result

    async def get_activity_summary(self) -> list:
        """Aggregate logs by user: count and last_seen timestamp."""
        pipeline = [
            {"$group": {
                "_id": "$user_id",
                "count": {"$sum": 1},
                "last_seen": {"$max": "$timestamp"}
            }},
            {"$sort": {"last_seen": -1}}
        ]
        cursor = self.logs_collection.aggregate(pipeline)
        result = []
        async for doc in cursor:
            username = await self._resolve_username(doc["_id"])
            ts = doc.get("last_seen")
            result.append({
                "user_id": doc["_id"],
                "username": username,
                "count": doc["count"],
                "last_seen": ts.isoformat() if ts else None,
            })
        return result

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
            quote_counts = {}
            for q_id in doc["quotes"]:
                quote_counts[q_id] = quote_counts.get(q_id, 0) + 1
            
            most_used_id = max(quote_counts, key=lambda k: quote_counts[k]) if quote_counts else None
            most_used_quote = await self.get_by_id(most_used_id) if most_used_id else None
            
            # Always resolve the latest username from user_id
            username = await self._resolve_username(doc["_id"])
            
            stats.append({
                "user_id": doc["_id"],
                "username": username,
                "total_shown": doc["total_quotes"],
                "most_used_content": most_used_quote.content if most_used_quote else "N/A"
            })
        return stats
