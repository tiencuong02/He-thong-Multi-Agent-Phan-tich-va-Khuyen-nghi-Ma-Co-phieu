from app.services.alpha_vantage import AlphaVantageService
import asyncio
import logging

logger = logging.getLogger(__name__)

async def research_stock(symbol: str):
    """
    Market Researcher: Gather historical price data and latest news.
    Augmented with Playwright browser automation for real-time news.
    """
    logger.info(f"[RESEARCHER] Starting data collection for {symbol}")
    
    # Run API tasks concurrently
    price_task = AlphaVantageService.fetch_stock_data(symbol)
    news_api_task = AlphaVantageService.fetch_news_sentiment(symbol)
    
    price_res, news_api_res = await asyncio.gather(
        price_task, news_api_task
    )
    news_web_res = []
    
    if "error" in price_res:
        return price_res
        
    combined_news = news_api_res + news_web_res

    # Detect nguồn tin tức thực tế
    news_from_yfinance = any(item.get("__source") == "yfinance" for item in combined_news)
    news_source = "yfinance" if news_from_yfinance else ("Alpha Vantage" if combined_news else "none")

    return {
        "symbol": symbol,
        "prices": price_res.get("prices", []),
        "news": combined_news,
        "fallback": price_res.get("fallback", False),
        "data_source": price_res.get("data_source", "Unknown"),
        "metadata": {
            "source_count": len(combined_news),
            "news_available": len(combined_news) > 0,
            "news_source": news_source,
        }
    }
