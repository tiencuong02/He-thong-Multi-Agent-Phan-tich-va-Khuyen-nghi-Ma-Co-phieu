from app.services.alpha_vantage import AlphaVantageService
from app.agents.tools.browser_tool import BrowserTool
import asyncio
import logging

logger = logging.getLogger(__name__)

async def research_stock(symbol: str):
    """
    Market Researcher: Gather historical price data and latest news.
    Augmented with Playwright browser automation for real-time news.
    """
    logger.info(f"[RESEARCHER] Starting data collection for {symbol}")
    
    # Run API and Browser tasks concurrently
    price_task = AlphaVantageService.fetch_stock_data(symbol)
    news_api_task = AlphaVantageService.fetch_news_sentiment(symbol)
    news_web_task = BrowserTool.fetch_news_from_web(symbol)
    
    price_res, news_api_res, news_web_res = await asyncio.gather(
        price_task, news_api_task, news_web_task
    )
    
    if "error" in price_res:
        return price_res
        
    combined_news = news_api_res + news_web_res
    
    return {
        "symbol": symbol,
        "prices": price_res.get("prices", []),
        "news": combined_news,
        "metadata": {
            "source_count": len(combined_news),
            "browser_augmented": len(news_web_res) > 0
        }
    }
