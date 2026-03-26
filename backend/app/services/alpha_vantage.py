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
        
        # Smart Suffixing: If search fails, try with .VN suffix
        if ("Error Message" in data or "Information" in data or not data.get("Time Series (Daily)")) and not symbol.endswith(".VN"):
            vn_symbol = f"{symbol}.VN"
            print(f"[SERVICE] No data for {symbol}. Trying {vn_symbol}...")
            vn_params = params.copy()
            vn_params["symbol"] = vn_symbol
            vn_data = await cls._make_request(vn_params)
            if "Time Series (Daily)" in vn_data:
                data = vn_data
                symbol = vn_symbol # Update symbol for the rest of the function
                print(f"[SERVICE] Found data for {vn_symbol}!")
        
        # Check if we have valid time series data WITH enough points
        has_valid_data = False
        if "Time Series (Daily)" in data:
            ts = data["Time Series (Daily)"]
            if len(ts) >= 20: # Must have at least 20 days for financial analyst
                has_valid_data = True

        if has_valid_data:
            ts = data["Time Series (Daily)"]
            result = []
            
            # Convert to list and slice to get last 100 days
            ts_items = list(ts.items())
            num_days = min(len(ts_items), 100)
            
            for i in range(num_days):
                date, val = ts_items[i]
                result.append({
                    "date": date,
                    "open": float(val["1. open"]),
                    "high": float(val["2. high"]),
                    "low": float(val["3. low"]),
                    "close": float(val["4. close"]),
                    "volume": int(val["5. volume"])
                })
            
            # Cache for 10 minutes
            await CacheService.set("history", symbol, result) 
            print(f"[SERVICE] Successfully fetched {len(result)} days for {symbol}")
            return {"symbol": symbol, "prices": result}
        
        # If we hit an error (rate limit/api error) OR data is insufficient, use mock fallback
        error_type = data.get("error", "insufficient_data")
        error_msg = data.get("message", f"Alpha Vantage returned {len(data.get('Time Series (Daily)', {}))} days, but 20+ are required.")
        
        if "Information" in data:
            error_type = "api_info"
            error_msg = data["Information"]
            
        print(f"[SERVICE] Data issue for {symbol} ({error_type}): {error_msg}. Using mock fallback.")
        mock_prices = cls._get_mock_data(symbol)
        return {
            "symbol": symbol, 
            "prices": mock_prices, 
            "fallback": True, 
            "api_error": error_type,
            "original_message": error_msg
        }

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
            
            if "Information" in data:
                return {"error": "api_info", "message": data["Information"]}
            
            if "Error Message" in data:
                return {"error": "api_error", "message": data["Error Message"]}
            
            return data
        except Exception as e:
            return {"error": "connection_error", "message": str(e)}

    @classmethod
    def _get_mock_data(cls, symbol: str) -> List[Dict[str, Any]]:
        """
        Generates 100 days of realistic mock OHLC data for fallback.
        """
        import random
        from datetime import datetime, timedelta
        
        print(f"[SERVICE] Generating 100 days of mock data for {symbol}")
        prices = []
        current_price = 150.0 + random.uniform(-10, 10)
        base_date = datetime.now()
        
        for i in range(100):
            date_str = (base_date - timedelta(days=i)).strftime("%Y-%m-%d")
            # Simple random walk
            change = current_price * random.uniform(-0.02, 0.02)
            open_p = current_price
            close_p = current_price + change
            high_p = max(open_p, close_p) + random.uniform(0, 2)
            low_p = min(open_p, close_p) - random.uniform(0, 2)
            volume = random.randint(1000000, 5000000)
            
            prices.append({
                "date": date_str,
                "open": round(open_p, 2),
                "high": round(high_p, 2),
                "low": round(low_p, 2),
                "close": round(close_p, 2),
                "volume": volume
            })
            current_price = close_p
            
        return prices

    @classmethod
    def get_pe_ratio(cls, symbol: str) -> Optional[float]:
        # This would use OVERVIEW, but the requirement specifically mentioned 
        # TIME_SERIES_DAILY and NEWS_SENTIMENT. 
        # I'll stick to the requirements for now.
        pass
