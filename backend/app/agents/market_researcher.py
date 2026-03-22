from app.services.alpha_vantage import AlphaVantageService
import asyncio

async def research_stock(symbol: str):
    """
    Market Researcher: Gather historical price data and latest news.
    """
    price_res = await AlphaVantageService.fetch_stock_data(symbol)
    news_res = await AlphaVantageService.fetch_news_sentiment(symbol)
    
    if "error" in price_res:
        return price_res # Propagate error
        
    return {
        "symbol": symbol,
        "prices": price_res.get("prices", []),
        "news": news_res
    }
