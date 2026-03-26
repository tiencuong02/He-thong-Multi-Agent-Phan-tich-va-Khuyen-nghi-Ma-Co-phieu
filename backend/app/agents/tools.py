import os
import requests
import json
from app.db.cache_service import CacheService
from textblob import TextBlob

ALPHA_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")

def fetch_stock_data(ticker: str) -> str:
    """
    Fetches historical price data (daily) for a given stock ticker from Alpha Vantage.
    Includes open, high, low, close prices and volume for the last 5 days.
    """
    cached = CacheService.get_sync("history", ticker)
    if cached:
        return cached

    try:
        url = "https://www.alphavantage.co/query"
        params = {
            "function": "TIME_SERIES_DAILY",
            "symbol": ticker,
            "apikey": ALPHA_API_KEY
        }

        res = requests.get(url, params=params, timeout=10)
        data = res.json()

        if "Note" in data:
            return f"Alpha Vantage API limit reached: {data['Note']}"
        if "Information" in data:
            return f"Alpha Vantage Info: {data['Information']}"
        if "Error Message" in data:
            return f"Alpha Vantage Error: {data['Error Message']}"

        ts = data.get("Time Series (Daily)", {})
        result = []

        # Increase from 5 to 100 days to match system requirements
        for date, val in list(ts.items())[:100]:
            result.append({
                "date": date,
                "open": val["1. open"],
                "high": val["2. high"],
                "low": val["3. low"],
                "close": val["4. close"],
                "volume": val["5. volume"]
            })

        result_json = json.dumps(result)
        CacheService.set_sync("history", ticker, result_json)
        return result_json

    except Exception as e:
        return f"Error fetching stock data: {str(e)}"

def fetch_fundamentals(ticker: str) -> str:
    """
    Fetches fundamental financial metrics for a given stock ticker from Alpha Vantage.
    Includes PE ratio, EPS, Market Cap, Dividend Yield, and Profit Margin.
    """
    cached = CacheService.get_sync("price", ticker)
    if cached:
        return cached

    try:
        url = "https://www.alphavantage.co/query"
        params = {
            "function": "OVERVIEW",
            "symbol": ticker,
            "apikey": ALPHA_API_KEY
        }

        res = requests.get(url, params=params, timeout=10)
        data = res.json()

        if "Note" in data:
            return f"Alpha Vantage API limit reached: {data['Note']}"
        if "Information" in data:
            return f"Alpha Vantage Info: {data['Information']}"
        if "Error Message" in data:
            return f"Alpha Vantage Error: {data['Error Message']}"

        result = {
            "pe": data.get("PERatio"),
            "eps": data.get("EPS"),
            "marketCap": data.get("MarketCapitalization"),
            "dividendYield": data.get("DividendYield"),
            "profitMargin": data.get("ProfitMargin")
        }

        result_json = json.dumps(result)
        CacheService.set_sync("price", ticker, result_json)
        return result_json

    except Exception as e:
        return f"Error fetching fundamentals: {str(e)}"

def fetch_news(ticker: str) -> str:
    """
    Fetches the latest news articles and sentiment feed for a given stock ticker from Alpha Vantage.
    Provides titles, links, and sources for recent news.
    """
    cached = CacheService.get_sync("news", ticker)
    if cached:
        return cached

    try:
        url = "https://www.alphavantage.co/query"
        params = {
            "function": "NEWS_SENTIMENT",
            "tickers": ticker,
            "apikey": ALPHA_API_KEY
        }

        res = requests.get(url, params=params, timeout=10)
        data = res.json()

        if "Note" in data:
            return f"Alpha Vantage API limit reached: {data['Note']}"
        if "Information" in data:
            return f"Alpha Vantage Info: {data['Information']}"
        if "Error Message" in data:
            return f"Alpha Vantage Error: {data['Error Message']}"

        feed = data.get("feed", [])

        news_list = [
            {
                "title": n.get("title"),
                "link": n.get("url"),
                "source": n.get("source")
            }
            for n in feed[:10]
        ]

        result_json = json.dumps(news_list)
        CacheService.set_sync("news", ticker, result_json)
        return result_json

    except Exception as e:
        return f"Error fetching news: {str(e)}"

def analyze_sentiment(news_text: str) -> str:
    """Analyzes the sentiment of a given text and returns a score between -1 (negative) and 1 (positive)."""
    try:
        blob = TextBlob(news_text)
        return json.dumps({"polarity": blob.sentiment.polarity, "subjectivity": blob.sentiment.subjectivity})
    except Exception as e:
        return f"Error analyzing sentiment: {str(e)}"
