"""
VnNewsService — tin tức chứng khoán Việt Nam.

Nguồn (ưu tiên theo thứ tự):
  1. CafeF RSS   — tin thị trường chung + lọc theo tên công ty
  2. Vietstock   — RSS tin tức doanh nghiệp
  3. AlphaVantage NEWS_SENTIMENT — fallback cho mã US hoặc khi VN sources lỗi

RSS không cần API key, fetch nhanh, phù hợp cho chatbot real-time.
"""

import asyncio
import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List, Dict, Any, Optional

import aiohttp

logger = logging.getLogger(__name__)

_TIMEOUT = aiohttp.ClientTimeout(total=8, connect=4)
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
}

# RSS feeds VN
_RSS_FEEDS = {
    "cafef_ck":    "https://cafef.vn/chung-khoan.rss",
    "cafef_market":"https://cafef.vn/thi-truong-chung-khoan.rss",
    "vietstock":   "https://vietstock.vn/771/chung-khoan.htm",
}

# Map mã ticker → tên công ty phổ biến để filter RSS
_TICKER_NAMES: Dict[str, List[str]] = {
    "FPT":  ["FPT", "Tập đoàn FPT"],
    "VNM":  ["Vinamilk", "VNM", "sữa"],
    "VCB":  ["Vietcombank", "VCB"],
    "TCB":  ["Techcombank", "TCB"],
    "HPG":  ["Hòa Phát", "HPG", "thép"],
    "VIC":  ["Vingroup", "VIC"],
    "VHM":  ["Vinhomes", "VHM"],
    "MBB":  ["MB Bank", "MBB", "Quân Đội"],
    "ACB":  ["ACB", "Á Châu"],
    "BID":  ["BIDV", "BID"],
    "CTG":  ["Vietinbank", "CTG"],
    "SSI":  ["SSI", "chứng khoán SSI"],
    "VPB":  ["VPBank", "VPB"],
    "MSN":  ["Masan", "MSN"],
    "GAS":  ["PV Gas", "GAS"],
    "SAB":  ["Sabeco", "SAB", "bia"],
    "VJC":  ["Vietjet", "VJC"],
    "MWG":  ["Thế Giới Di Động", "MWG"],
    "HDB":  ["HD Bank", "HDB"],
    "PLX":  ["Petrolimex", "PLX"],
}


class VnNewsService:

    @classmethod
    async def fetch_news(
        cls,
        ticker: Optional[str] = None,
        max_items: int = 8,
    ) -> List[Dict[str, Any]]:
        """
        Lấy tin tức.
        - ticker=None → tin thị trường chung từ CafeF
        - ticker="FPT" → lọc tin liên quan đến FPT từ RSS + AlphaVantage fallback
        """
        vn_news = await cls._fetch_cafef_rss(ticker, max_items * 2)

        if len(vn_news) < 3 and ticker:
            # Thêm từ AlphaVantage nếu RSS không đủ
            av_news = await cls._fetch_av_news(ticker, max_items)
            vn_news = vn_news + av_news

        return vn_news[:max_items]

    @classmethod
    def format_for_llm(cls, ticker: Optional[str], news: List[Dict[str, Any]]) -> str:
        if not news:
            subject = f"mã {ticker}" if ticker else "thị trường"
            return f"Hiện không tìm thấy tin tức mới về {subject}."

        subject = f"mã {ticker}" if ticker else "thị trường chứng khoán"
        lines   = [f"=== TIN TỨC {subject.upper()} ===", ""]

        for i, item in enumerate(news, 1):
            title  = item.get("title", "")
            source = item.get("source", "")
            pub    = item.get("published", "")
            url    = item.get("url",   "")
            sentiment = item.get("sentiment", "")

            s_icon = {"Bullish": "📈", "Bearish": "📉", "Neutral": "📰"}.get(sentiment, "📰")
            lines.append(f"{i}. {s_icon} {title}")
            if pub:
                lines.append(f"   🕐 {pub}  |  Nguồn: {source}")
            if url:
                lines.append(f"   🔗 {url}")
            lines.append("")

        return "\n".join(lines)

    # ─── Internal ─────────────────────────────────────────────────────────────

    @classmethod
    async def _fetch_cafef_rss(
        cls, ticker: Optional[str], limit: int
    ) -> List[Dict[str, Any]]:
        """Fetch CafeF RSS + filter theo ticker nếu có."""
        feeds = list(_RSS_FEEDS.values())
        results = await asyncio.gather(
            *[cls._parse_rss(url) for url in feeds],
            return_exceptions=True,
        )

        all_items: List[Dict[str, Any]] = []
        for items in results:
            if isinstance(items, Exception):
                continue
            all_items.extend(items)

        # Dedup theo title
        seen: set = set()
        unique = []
        for item in all_items:
            key = item.get("title", "")[:60]
            if key not in seen:
                seen.add(key)
                unique.append(item)

        if ticker:
            keywords = _TICKER_NAMES.get(ticker.upper(), [ticker.upper()])
            filtered = [
                i for i in unique
                if any(kw.lower() in i.get("title", "").lower() or
                       kw.lower() in i.get("description", "").lower()
                       for kw in keywords)
            ]
            return filtered[:limit] if filtered else unique[:limit // 2]

        return unique[:limit]

    @classmethod
    async def _parse_rss(cls, url: str) -> List[Dict[str, Any]]:
        """Parse RSS/Atom feed thành list dict chuẩn."""
        try:
            async with aiohttp.ClientSession(
                headers=_HEADERS, timeout=_TIMEOUT
            ) as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        return []
                    text = await resp.text(errors="replace")

            root = ET.fromstring(text)
            ns = {"atom": "http://www.w3.org/2005/Atom"}

            items = root.findall(".//item")  # RSS
            if not items:
                items = root.findall(".//atom:entry", ns)  # Atom

            out = []
            for item in items[:20]:
                title = (
                    cls._tag(item, "title") or
                    cls._tag(item, "atom:title", ns) or ""
                ).strip()
                link = (
                    cls._tag(item, "link") or
                    cls._tag(item, "atom:link", ns) or ""
                ).strip()
                desc = (
                    cls._tag(item, "description") or
                    cls._tag(item, "atom:summary", ns) or ""
                )
                pub = (
                    cls._tag(item, "pubDate") or
                    cls._tag(item, "atom:published", ns) or ""
                )[:20]

                # Clean HTML tags từ description
                desc_clean = re.sub(r"<[^>]+>", "", desc)[:200].strip()

                if title:
                    out.append({
                        "title":       title,
                        "url":         link,
                        "description": desc_clean,
                        "published":   pub,
                        "source":      cls._domain(url),
                        "sentiment":   "Neutral",
                    })
            return out

        except ET.ParseError as e:
            logger.debug(f"RSS parse error {url}: {e}")
            return []
        except Exception as e:
            logger.warning(f"RSS fetch error {url}: {e}")
            return []

    @classmethod
    async def _fetch_av_news(cls, ticker: str, limit: int) -> List[Dict[str, Any]]:
        """AlphaVantage NEWS_SENTIMENT — fallback cho khi RSS thiếu."""
        try:
            from app.services.alpha_vantage import AlphaVantageService
            raw = await AlphaVantageService.fetch_news_sentiment(ticker)
            out = []
            for item in raw[:limit]:
                title = item.get("title", "")
                if not title:
                    continue
                sentiment_label = item.get("overall_sentiment_label", "Neutral")
                out.append({
                    "title":     title,
                    "url":       item.get("url", ""),
                    "published": item.get("time_published", "")[:16],
                    "source":    item.get("source", "AlphaVantage"),
                    "sentiment": sentiment_label,
                })
            return out
        except Exception as e:
            logger.debug(f"AV news fallback error: {e}")
            return []

    @staticmethod
    def _tag(element: ET.Element, tag: str, ns: dict = None) -> str:
        try:
            child = element.find(tag, ns) if ns else element.find(tag)
            if child is None:
                return ""
            return (child.text or "").strip()
        except Exception:
            return ""

    @staticmethod
    def _domain(url: str) -> str:
        m = re.search(r"https?://(?:www\.)?([^/]+)", url)
        return m.group(1) if m else url
