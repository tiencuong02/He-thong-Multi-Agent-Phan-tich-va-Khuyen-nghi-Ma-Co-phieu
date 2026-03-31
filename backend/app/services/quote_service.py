import random
import json
from typing import List, Optional
from app.repositories.quote_repository import QuoteRepository
from app.models.quote import Quote, QuoteCreate, QuoteUpdate, QuoteLog, QuoteContext
from app.db.redis import redis_instance

class QuoteService:
    def __init__(self, quote_repo: QuoteRepository):
        self.quote_repo = quote_repo
        self.redis = redis_instance

    async def get_quotes(self) -> List[Quote]:
        return await self.quote_repo.get_all()

    async def get_random_quote(self, user_id: str, context: QuoteContext = QuoteContext.HOLD) -> Optional[Quote]:
        quotes = await self.quote_repo.get_by_context(context)
        if not quotes:
            # Fallback to HOLD if context specific not found
            quotes = await self.quote_repo.get_by_context(QuoteContext.HOLD)
        
        if not quotes:
            return None

        # Logic to avoid showing the same quote too frequently
        # Key: last_quotes:{user_id}
        cache_key = f"last_quotes:{user_id}"
        if not self.redis or not self.redis.client:
            return random.choice(quotes)
            
        last_quotes_json = await self.redis.client.get(cache_key)
        last_quote_ids = json.loads(last_quotes_json) if last_quotes_json else []
        
        # Filter out quotes shown in last 3 times
        available_quotes = [q for q in quotes if q.id not in last_quote_ids]
        
        # If all were shown, reset and pick from all
        selected_quote = random.choice(available_quotes if available_quotes else quotes)
        
        # Update cache (keep last 3)
        last_quote_ids.append(selected_quote.id)
        if len(last_quote_ids) > 3:
            last_quote_ids.pop(0)
        
        await self.redis.client.set(cache_key, json.dumps(last_quote_ids), ex=3600*24) # 1 day exp

        # Log the quote shown
        log = QuoteLog(
            user_id=user_id,
            quote_id=selected_quote.id,
            context=context
        )
        await self.quote_repo.log_quote_shown(log)
        
        return selected_quote

    async def create_quote(self, quote_in: QuoteCreate) -> Quote:
        return await self.quote_repo.create(quote_in)

    async def update_quote(self, quote_id: str, quote_in: QuoteUpdate) -> Optional[Quote]:
        return await self.quote_repo.update(quote_id, quote_in)

    async def delete_quote(self, quote_id: str) -> bool:
        return await self.quote_repo.delete(quote_id)

    async def get_overall_stats(self) -> dict:
        return await self.quote_repo.get_admin_summary()

    async def get_user_stats(self) -> List[dict]:
        return await self.quote_repo.get_user_stats()

    async def get_recent_logs(self, limit: int = 20, skip: int = 0, user_id: str = None) -> list:
        return await self.quote_repo.get_recent_logs(limit=limit, skip=skip, user_id=user_id)

    async def get_activity_summary(self) -> list:
        return await self.quote_repo.get_activity_summary()

    async def seed_quotes(self):
        # Initial seed if empty
        quotes = await self.get_quotes()
        if not quotes:
            initial_quotes = [
                {"content": "Be fearful when others are greedy and greedy when others are fearful.", "author": "Warren Buffett", "context": "BUY"},
                {"content": "The stock market is designed to transfer money from the Active to the Patient.", "author": "Warren Buffett", "context": "HOLD"},
                {"content": "Wide diversification is only required when investors do not understand what they are doing.", "author": "Warren Buffett", "context": "HOLD"},
                {"content": "In the short run, the market is a voting machine but in the long run, it is a weighing machine.", "author": "Benjamin Graham", "context": "HOLD"},
                {"content": "Know what you own, and know why you own it.", "author": "Peter Lynch", "context": "BUY"},
                {"content": "The best time to sell is when everyone is buying.", "author": "Anonymous", "context": "SELL"},
                {"content": "Buy low, sell high. It's simple, but not easy.", "author": "Anonymous", "context": "HOLD"},
            ]
            for q in initial_quotes:
                await self.create_quote(QuoteCreate(**q))
