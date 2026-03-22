import os
import requests
import json
import time
import asyncio
from typing import Optional, Dict, Any, List, cast
from app.db.cache_service import CacheService

class AlphaVantageService:
    API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
    BASE_URL = "https://www.alphavantage.co/query"

    @classmethod
    async def fetch_stock_data(cls, symbol: str) -> Dict[str, Any]:
        """
        Fetches TIME_SERIES_DAILY for a symbol.
        Checks Redis cache first. Handles rate limits.
        """
        cached = await CacheService.get("history", symbol)
        if cached:
            prices = cached if isinstance(cached, list) else json.loads(cached)
            return {"symbol": symbol, "prices": prices}

        params = {
            "function": "TIME_SERIES_DAILY",
            "symbol": symbol,
            "apikey": cls.API_KEY
        }

        data = await cls._make_request(params)
        
        if "Time Series (Daily)" in data:
            ts = data["Time Series (Daily)"]
            result = []
            
            # Convert to list and slice to get last 20 days
            ts_items = list(ts.items())
            for i in range(min(len(ts_items), 20)):
                date, val = ts_items[i]
                result.append({
                    "date": date,
                    "open": float(val["1. open"]),
                    "high": float(val["2. high"]),
                    "low": float(val["3. low"]),
                    "close": float(val["4. close"]),
                    "volume": int(val["5. volume"])
                })
            
            # Cache for 10 seconds as requested
            await CacheService.set("history", symbol, result) 
            return {"symbol": symbol, "prices": result}
        
        return data

    @classmethod
    async def fetch_news_sentiment(cls, symbol: str) -> List[Dict[str, Any]]:
        """
        Fetches NEWS_SENTIMENT for a symbol.
        """
        params = {
            "function": "NEWS_SENTIMENT",
            "tickers": symbol,
            "apikey": cls.API_KEY
        }
        
        data = await cls._make_request(params)
        return data.get("feed", [])

    @classmethod
    async def _make_request(cls, params: Dict[str, str]) -> Dict[str, Any]:
        """
        Makes a request to Alpha Vantage and handles rate limiting.
        """
        try:
            # Using asyncio.to_thread for synchronous requests call
            response = await asyncio.to_thread(requests.get, cls.BASE_URL, params=params, timeout=10)
            data = response.json()

            if "Note" in data:
                # Rate limit hit: "Thank you for using Alpha Vantage! Our standard API call frequency is 5 calls per minute..."
                print(f"Alpha Vantage Rate Limit Hit: {data['Note']}")
                # In a real app, we might wait and retry, but for now we return the error
                # or a specific signal to the caller.
                return {"error": "rate_limit", "message": data["Note"]}
            
            if "Error Message" in data:
                return {"error": "api_error", "message": data["Error Message"]}
            
            return data
        except Exception as e:
            return {"error": "connection_error", "message": str(e)}

    @classmethod
    def get_pe_ratio(cls, symbol: str) -> Optional[float]:
        # This would use OVERVIEW, but the requirement specifically mentioned 
        # TIME_SERIES_DAILY and NEWS_SENTIMENT. 
        # I'll stick to the requirements for now.
        pass
