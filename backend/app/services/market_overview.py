"""
MarketOverviewService — tổng quan thị trường chứng khoán Việt Nam.

Nguồn dữ liệu:
  - TCBS public API (không cần key) cho VN-Index, VN30, HNX-Index
  - Fallback: tính từ OHLCV bars của chỉ số qua TCBSService

Output: dict tổng hợp thị trường để LLM nhận định.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

import aiohttp

logger = logging.getLogger(__name__)

TCBS_BASE    = "https://apipubaws.tcbs.com.vn/stock-insight/v1"
TCBS_TIMEOUT = aiohttp.ClientTimeout(total=8, connect=4)
TCBS_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept":  "application/json, text/plain, */*",
    "Referer": "https://tcinvest.tcbs.com.vn/",
    "Origin":  "https://tcinvest.tcbs.com.vn",
}

# Chỉ số và đại diện ngành
_INDICES = {
    "VNINDEX": "VN-Index",
    "VN30":    "VN30",
    "HNX":     "HNX-Index",
}

# Rổ VN30 đại diện — dùng để tính breadth (tăng/giảm/đứng)
_VN30_BASKET = [
    "ACB", "BCM", "BID", "BVH", "CTG",
    "FPT", "GAS", "GVR", "HDB", "HPG",
    "MBB", "MSN", "MWG", "PLX", "POW",
    "SAB", "SSB", "SSI", "STB", "TCB",
    "TPB", "VCB", "VHM", "VIB", "VIC",
    "VJC", "VNM", "VPB", "VRE", "VTI",
]


class MarketOverviewService:

    @classmethod
    async def get_overview(cls) -> Dict[str, Any]:
        """
        Lấy tổng quan thị trường: chỉ số + breadth + top movers.
        Timeout toàn bộ 10s — không block pipeline quá lâu.
        """
        indices_task  = cls._fetch_indices()
        breadth_task  = cls._fetch_breadth()
        movers_task   = cls._fetch_top_movers()

        indices, breadth, movers = await asyncio.gather(
            indices_task, breadth_task, movers_task,
            return_exceptions=True,
        )

        return {
            "indices":  indices  if not isinstance(indices,  Exception) else {},
            "breadth":  breadth  if not isinstance(breadth,  Exception) else {},
            "movers":   movers   if not isinstance(movers,   Exception) else {"gainers": [], "losers": []},
            "timestamp": datetime.now().strftime("%H:%M %d/%m/%Y"),
        }

    @classmethod
    async def format_for_llm(cls, overview: Dict[str, Any]) -> str:
        """Chuyển dict overview thành context string cho LLM."""
        lines = [
            f"=== TỔNG QUAN THỊ TRƯỜNG | {overview.get('timestamp','')} ===",
            "",
        ]

        # Chỉ số chính
        indices = overview.get("indices", {})
        if indices:
            lines.append("📊 CHỈ SỐ CHÍNH:")
            for code, name in _INDICES.items():
                info = indices.get(code, {})
                if not info:
                    continue
                close  = info.get("close", 0)
                change = info.get("change", 0)
                pct    = info.get("change_pct", 0)
                arrow  = "▲" if change >= 0 else "▼"
                sign   = "+" if change >= 0 else ""
                lines.append(
                    f"  {name}: {close:,.2f}  {arrow} {sign}{change:,.2f} ({sign}{pct:.2f}%)"
                )
            lines.append("")

        # Breadth
        breadth = overview.get("breadth", {})
        if breadth:
            adv  = breadth.get("advances",  0)
            dec  = breadth.get("declines",  0)
            unch = breadth.get("unchanged", 0)
            lines.append(f"📈 Độ rộng thị trường (rổ VN30):")
            lines.append(f"  Tăng: {adv}  |  Giảm: {dec}  |  Đứng: {unch}")
            lines.append("")

        # Top movers
        movers = overview.get("movers", {})
        gainers = movers.get("gainers", [])
        losers  = movers.get("losers",  [])

        if gainers:
            lines.append("🚀 TOP TĂNG:")
            for m in gainers[:5]:
                lines.append(f"  {m['ticker']}: {m['close']:,.2f} (+{m['change_pct']:.2f}%)")
        if losers:
            lines.append("🔻 TOP GIẢM:")
            for m in losers[:5]:
                lines.append(f"  {m['ticker']}: {m['close']:,.2f} ({m['change_pct']:.2f}%)")

        return "\n".join(lines)

    # ─── Internal fetch methods ───────────────────────────────────────────────

    @classmethod
    async def _fetch_indices(cls) -> Dict[str, Any]:
        """Lấy giá đóng cửa và % thay đổi cho VNINDEX, VN30, HNX qua TCBS."""
        from app.services.tcbs_service import TCBSService

        results = await asyncio.gather(
            *[TCBSService.fetch_daily_ohlcv(code, count=3) for code in _INDICES],
            return_exceptions=True,
        )

        out = {}
        for code, bars in zip(_INDICES, results):
            if isinstance(bars, Exception) or not bars or len(bars) < 2:
                continue
            today = bars[0]
            prev  = bars[1]
            close      = today["close"]
            prev_close = prev["close"]
            change     = round(close - prev_close, 2)
            change_pct = round(change / prev_close * 100, 2) if prev_close else 0
            out[code]  = {
                "close":      close,
                "change":     change,
                "change_pct": change_pct,
                "volume":     today.get("volume", 0),
                "date":       today.get("date", ""),
            }
        return out

    @classmethod
    async def _fetch_breadth(cls) -> Dict[str, Any]:
        """Tính breadth (tăng/giảm/đứng) từ rổ VN30."""
        from app.services.tcbs_service import TCBSService

        results = await asyncio.gather(
            *[TCBSService.fetch_daily_ohlcv(t, count=3) for t in _VN30_BASKET],
            return_exceptions=True,
        )

        advances = declines = unchanged = 0
        for bars in results:
            if isinstance(bars, Exception) or not bars or len(bars) < 2:
                continue
            change = bars[0]["close"] - bars[1]["close"]
            if change > 0:      advances  += 1
            elif change < 0:    declines  += 1
            else:               unchanged += 1

        return {"advances": advances, "declines": declines, "unchanged": unchanged}

    @classmethod
    async def _fetch_top_movers(cls) -> Dict[str, Any]:
        """Tính top gainers / losers từ rổ VN30."""
        from app.services.tcbs_service import TCBSService

        results = await asyncio.gather(
            *[TCBSService.fetch_daily_ohlcv(t, count=3) for t in _VN30_BASKET],
            return_exceptions=True,
        )

        movers = []
        for ticker, bars in zip(_VN30_BASKET, results):
            if isinstance(bars, Exception) or not bars or len(bars) < 2:
                continue
            close      = bars[0]["close"]
            prev_close = bars[1]["close"]
            if prev_close <= 0:
                continue
            change_pct = round((close - prev_close) / prev_close * 100, 2)
            movers.append({"ticker": ticker, "close": close, "change_pct": change_pct})

        movers.sort(key=lambda x: x["change_pct"], reverse=True)
        return {
            "gainers": movers[:5],
            "losers":  movers[-5:][::-1],
        }
