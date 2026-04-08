import os
import requests
import json
import time
import asyncio
import yfinance as yf
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, cast
from app.db.cache_service import CacheService
from app.core.config import settings

class AlphaVantageService:
    BASE_URL = "https://www.alphavantage.co/query"

    @classmethod
    async def fetch_stock_data(cls, symbol: str) -> Dict[str, Any]:
        """
        Fetches daily data for a symbol using yfinance (primary) or Alpha Vantage 
        Checks Redis cache first.
        """
        cached = await CacheService.get("history", symbol)
        if cached:
            prices = cached if isinstance(cached, list) else json.loads(cached)
            return {"symbol": symbol, "prices": prices, "fallback": False}

        print(f"[SERVICE] Fetching {symbol} from Yahoo Finance...")
        try:
            primary_symbol = symbol
            fallback_symbol = f"{symbol}.VN" if not symbol.endswith(".VN") else symbol

            # For 3-letter symbols without dots, they are likely VN stocks, so prioritize .VN
            if len(symbol) == 3 and "." not in symbol and symbol.isalpha():
                primary_symbol = f"{symbol}.VN"
                fallback_symbol = symbol

            # yfinance is synchronous, wrapping in to_thread
            ticker = yf.Ticker(primary_symbol)
            # Fetch last 6 months to ensure we have 100 days
            df = await asyncio.to_thread(ticker.history, period="6mo")
            
            if df.empty and primary_symbol != fallback_symbol:
                print(f"[SERVICE] No data for {primary_symbol}. Trying {fallback_symbol}...")
                ticker = yf.Ticker(fallback_symbol)
                df = await asyncio.to_thread(ticker.history, period="6mo")
                if not df.empty:
                    symbol = fallback_symbol
            else:
                symbol = primary_symbol

            if not df.empty:
                result = []
                # Sort by date descending (most recent first)
                df = df.sort_index(ascending=False)
                
                import math
                num_days = min(len(df), 100)
                for date, row in df.head(num_days).iterrows():
                    close = float(row["Close"])
                    if math.isnan(close) or math.isinf(close):
                        continue
                    result.append({
                        "date": date.strftime("%Y-%m-%d"),
                        "open": round(float(row["Open"]), 2),
                        "high": round(float(row["High"]), 2),
                        "low": round(float(row["Low"]), 2),
                        "close": round(close, 2),
                        "volume": int(row["Volume"]) if not math.isnan(float(row["Volume"])) else 0
                    })
                
                # Cache for 10 minutes
                await CacheService.set("history", symbol, result)
                print(f"[SERVICE] Successfully fetched {len(result)} days for {symbol} via yfinance")
                return {"symbol": symbol, "prices": result, "fallback": False}
        
        except Exception as e:
            print(f"[SERVICE] yfinance error for {symbol}: {e}. Falling back to Alpha Vantage...")

        # --- FALLBACK TO ALPHA VANTAGE ---
        is_crypto = "-" in symbol or any(c in symbol.upper() for c in ["BTC", "ETH", "SOL", "BNB", "DOGE"])
        
        if is_crypto:
            crypto_symbol = symbol.split("-")[0]
            market = symbol.split("-")[1] if "-" in symbol else "USD"
            params = {
                "function": "DIGITAL_CURRENCY_DAILY",
                "symbol": crypto_symbol,
                "market": market,
                "apikey": settings.ALPHA_VANTAGE_API_KEY
            }
        else:
            params = {
                "function": "TIME_SERIES_DAILY",
                "symbol": symbol,
                "apikey": settings.ALPHA_VANTAGE_API_KEY
            }

        data = await cls._make_request(params)
        
        ts_key = "Time Series (Digital Currency Daily)" if is_crypto else "Time Series (Daily)"
        if ts_key in data:
            ts = data[ts_key]
            result = []
            ts_items = list(ts.items())
            num_days = min(len(ts_items), 100)
            
            for i in range(num_days):
                date, val = ts_items[i]
                if is_crypto:
                    open_key = next((k for k in val.keys() if "open" in k), "1a. open (USD)")
                    close_key = next((k for k in val.keys() if "close" in k), "4a. close (USD)")
                    result.append({
                        "date": date,
                        "open": float(val[open_key]),
                        "close": float(val[close_key]),
                        "high": float(val.get(next((k for k in val.keys() if "high" in k), ""), 0)),
                        "low": float(val.get(next((k for k in val.keys() if "low" in k), ""), 0)),
                        "volume": float(val.get("5. volume", 0))
                    })
                else:
                    result.append({
                        "date": date,
                        "open": float(val["1. open"]),
                        "high": float(val["2. high"]),
                        "low": float(val["3. low"]),
                        "close": float(val["4. close"]),
                        "volume": int(val["5. volume"])
                    })
            
            await CacheService.set("history", symbol, result)
            return {"symbol": symbol, "prices": result, "fallback": False}

        # Last resort: mock data
        print(f"[SERVICE] All data sources failed for {symbol}. Using mock fallback.")
        mock_prices = cls._get_mock_data(symbol)
        return {
            "symbol": symbol, 
            "prices": mock_prices, 
            "fallback": True, 
            "api_error": data.get("error", "total_failure")
        }

    @classmethod
    async def fetch_news_sentiment(cls, symbol: str) -> List[Dict[str, Any]]:
        """
        Fetches NEWS_SENTIMENT for a symbol.
        """
        params = {
            "function": "NEWS_SENTIMENT",
            "tickers": symbol,
            "apikey": settings.ALPHA_VANTAGE_API_KEY
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
                print(f"Alpha Vantage Rate Limit Hit: {data['Note']}")
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
