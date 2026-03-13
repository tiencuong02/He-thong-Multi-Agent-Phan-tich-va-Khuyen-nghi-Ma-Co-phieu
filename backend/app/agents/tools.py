from crewai.tools import tool
import yfinance as yf
from textblob import TextBlob
import json

@tool("Fetch Stock Data")
def fetch_stock_data(ticker: str) -> str:
    """Fetches historical stock price and volume data for a given ticker symbol."""
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1mo")
        # Keep it simple: return last 5 days
        return hist.tail(5).to_json(date_format='iso')
    except Exception as e:
        return f"Error fetching stock data: {str(e)}"

@tool("Fetch Fundamentals")
def fetch_fundamentals(ticker: str) -> str:
    """Fetches fundamental financial ratios like PE, EPS, Market Cap for a given ticker symbol."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        metrics = {
            "trailingPE": info.get("trailingPE"),
            "forwardPE": info.get("forwardPE"),
            "trailingEps": info.get("trailingEps"),
            "forwardEps": info.get("forwardEps"),
            "marketCap": info.get("marketCap"),
            "dividendYield": info.get("dividendYield"),
            "profitMargins": info.get("profitMargins")
        }
        return json.dumps(metrics)
    except Exception as e:
        return f"Error fetching fundamentals: {str(e)}"

@tool("Fetch News")
def fetch_news(ticker: str) -> str:
    """Fetches the latest news headlines for a given ticker symbol."""
    try:
        stock = yf.Ticker(ticker)
        news = stock.news
        if not news:
             return "No news found."
        news_list = [{"title": n.get("title"), "link": n.get("link"), "publisher": n.get("publisher")} for n in news[:10]]
        return json.dumps(news_list)
    except Exception as e:
        return f"Error fetching news: {str(e)}"

@tool("Analyze Sentiment")
def analyze_sentiment(news_text: str) -> str:
    """Analyzes the sentiment of a given text and returns a score between -1 (negative) and 1 (positive)."""
    try:
        blob = TextBlob(news_text)
        return json.dumps({"polarity": blob.sentiment.polarity, "subjectivity": blob.sentiment.subjectivity})
    except Exception as e:
        return f"Error analyzing sentiment: {str(e)}"
