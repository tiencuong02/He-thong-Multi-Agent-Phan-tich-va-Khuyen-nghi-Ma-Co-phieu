from app.services.alpha_vantage import AlphaVantageService
import asyncio

async def research_stock(symbol: str):
    """
    Market Researcher: Gather historical price data and latest news.
    """
    price_data = await AlphaVantageService.fetch_stock_data(symbol)
    news_data = await AlphaVantageService.fetch_news_sentiment(symbol)
    
    return {
        "prices": price_data,
        "news": news_data
    }
