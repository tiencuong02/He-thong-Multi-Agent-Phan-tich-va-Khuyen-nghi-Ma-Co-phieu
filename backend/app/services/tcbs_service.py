"""
TCBS (Techcombank Securities) Market Data Service.
Public API — không cần API key, dữ liệu VN market intraday (~15-20 phút delay).
Thay thế Yahoo Finance EOD cho cổ phiếu Việt Nam.
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

import aiohttp

logger = logging.getLogger(__name__)

TCBS_BASE    = "https://apipubaws.tcbs.com.vn/stock-insight/v1"
TCBS_TIMEOUT = aiohttp.ClientTimeout(total=8, connect=4)

# Mã US nổi tiếng có thể trùng với mã VN (ví dụ: ACB có thể là US hay VN)
# Danh sách này giúp phân biệt khi cần; hiện tại dùng heuristic đơn giản
_KNOWN_US_TICKERS = frozenset({
    "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "META", "NVDA", "TSLA",
    "BRK", "JPM", "JNJ", "V", "PG", "MA", "HD", "CVX", "MRK", "ABBV",
    "LLY", "PFE", "BAC", "XOM", "AVGO", "COST", "WMT", "DIS", "NFLX",
    "ADBE", "CRM", "ORCL", "INTC", "AMD", "QCOM", "TXN", "MU", "AMAT",
    "SPY", "QQQ", "IWM", "GLD", "SLV", "USO",
})

_TCBS_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://tcinvest.tcbs.com.vn/",
    "Origin":  "https://tcinvest.tcbs.com.vn",
}


class TCBSService:
    """
    Cung cấp OHLCV hàng ngày cho cổ phiếu Việt Nam qua TCBS public API.
    Interface tương thích với AlphaVantageService để swap dễ dàng.
    """

    @staticmethod
    def is_vn_ticker(ticker: str) -> bool:
        """
        Heuristic: mã VN thường là 2-5 chữ hoa, không dấu chấm, không số.
        Loại trừ các mã US phổ biến.
        """
        clean = ticker.replace(".VN", "").upper()
        return (
            2 <= len(clean) <= 5
            and clean.isalpha()
            and clean not in _KNOWN_US_TICKERS
        )

    @classmethod
    async def fetch_daily_ohlcv(
        cls,
        ticker: str,
        count: int = 100,
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Lấy lịch sử OHLCV từ TCBS (daily bars).
        Trả về list giảm dần (mới nhất trước), format chuẩn: date/open/high/low/close/volume.
        """
        clean_ticker = ticker.replace(".VN", "").upper()
        url = (
            f"{TCBS_BASE}/stock/{clean_ticker}/bars-long-term"
            f"?resolution=D&countBack={count}&type=stock"
        )
        try:
            async with aiohttp.ClientSession(
                headers=_TCBS_HEADERS, timeout=TCBS_TIMEOUT
            ) as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        logger.warning(f"TCBS HTTP {resp.status} for {clean_ticker}")
                        return None
                    payload = await resp.json(content_type=None)

            bars = payload.get("data", [])
            if not bars:
                logger.info(f"TCBS: no bars for {clean_ticker}")
                return None

            result = []
            # TCBS trả ascending → đảo thành descending (mới nhất trước)
            for bar in reversed(bars):
                ts = bar.get("tradingDate", "")
                try:
                    if isinstance(ts, (int, float)):
                        # epoch milliseconds
                        date_str = datetime.fromtimestamp(ts / 1000).strftime("%Y-%m-%d")
                    else:
                        date_str = str(ts)[:10]
                except Exception:
                    date_str = str(ts)[:10]

                close = float(bar.get("close", 0) or 0)
                if close <= 0:
                    continue  # bỏ nến rỗng

                result.append({
                    "date":   date_str,
                    "open":   round(float(bar.get("open",   close)), 2),
                    "high":   round(float(bar.get("high",   close)), 2),
                    "low":    round(float(bar.get("low",    close)), 2),
                    "close":  round(close, 2),
                    "volume": int(bar.get("volume", 0) or 0),
                })

            logger.info(f"TCBS: fetched {len(result)} days for {clean_ticker}")
            return result or None

        except asyncio.TimeoutError:
            logger.warning(f"TCBS timeout for {clean_ticker}")
            return None
        except aiohttp.ClientError as e:
            logger.error(f"TCBS network error for {clean_ticker}: {e}")
            return None
        except Exception as e:
            logger.error(f"TCBS unexpected error for {clean_ticker}: {e}")
            return None

    @classmethod
    async def fetch_stock_data(cls, ticker: str) -> Dict[str, Any]:
        """
        Drop-in replacement cho AlphaVantageService.fetch_stock_data().
        Trả về dict với keys: symbol, prices, fallback, data_source.
        """
        try:
            from app.db.cache_service import CacheService
            import json

            cache_key = f"tcbs_{ticker.upper()}"
            cached = await CacheService.get("history", cache_key)
            if cached:
                prices = cached if isinstance(cached, list) else json.loads(cached)
                logger.debug(f"TCBS cache hit for {ticker}")
                return {
                    "symbol":      ticker,
                    "prices":      prices,
                    "fallback":    False,
                    "data_source": "TCBS (cache)",
                }
        except Exception:
            pass  # cache miss hoặc lỗi → tiếp tục fetch

        prices = await cls.fetch_daily_ohlcv(ticker, count=100)
        if not prices:
            return {
                "symbol":      ticker,
                "prices":      [],
                "fallback":    True,
                "data_source": "TCBS (failed)",
            }

        try:
            from app.db.cache_service import CacheService
            await CacheService.set("history", f"tcbs_{ticker.upper()}", prices)
        except Exception:
            pass

        return {
            "symbol":      ticker,
            "prices":      prices,
            "fallback":    False,
            "data_source": "TCBS",
        }
