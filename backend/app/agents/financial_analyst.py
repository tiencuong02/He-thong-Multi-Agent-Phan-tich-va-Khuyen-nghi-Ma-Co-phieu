from typing import Dict, Any, List, Tuple

def _aggregate_news_sentiment(news: list) -> Tuple[float, str, int]:
    scores = []
    for item in news:
        score = item.get("overall_sentiment_score")
        ticker_sents = item.get("ticker_sentiment", [])
        relevance = float(ticker_sents[0].get("relevance_score", 0.5)) if ticker_sents else 0.5
        if score is not None:
            scores.append(float(score) * relevance)

    if not scores:
        return 0.0, "Trung lập", 0

    avg = sum(scores) / len(scores)
    label = "Tích cực" if avg > 0.15 else ("Tiêu cực" if avg < -0.15 else "Trung lập")
    return round(avg, 4), label, len(scores)

def analyze_financials(data: Dict[str, Any]):
    """
    Financial Analyst: Compute MA5, MA20, Trend, and Volume change.
    """
    prices = data.get("prices", [])
    if not isinstance(prices, list) or len(prices) < 20:
        return {"error": "Insufficient price data for analysis (need at least 20 days)"}

    # Prices are from newest to oldest
    closes: List[float] = [float(p["close"]) for p in prices]
    volumes: List[int] = [int(p["volume"]) for p in prices]

    ma5 = sum(closes[:5]) / 5
    ma20 = sum(closes[:20]) / 20
    
    # Optional: MA50 and MA100 if we have enough data (new requirement: fetch 100 days)
    ma50 = sum(closes[:50]) / 50 if len(closes) >= 50 else ma20
    ma100 = sum(closes[:100]) / 100 if len(closes) >= 100 else ma50
    
    # Trend: simplistic current vs previous price
    curr_price = closes[0]
    prev_price = closes[1]
    trend = "up" if curr_price > prev_price else "down"

    # Volume change: current vs avg of last 5
    curr_volume = volumes[0]
    avg_volume_5 = sum(volumes[1:6]) / 5
    volume_change = (curr_volume - avg_volume_5) / avg_volume_5 if avg_volume_5 > 0 else 0

    news = data.get("news", [])
    sentiment_score, sentiment_label, news_count = _aggregate_news_sentiment(news)

    return {
        "symbol": data.get("symbol"),
        "price": curr_price,
        "ma5": ma5,
        "ma20": ma20,
        "ma50": ma50,
        "ma100": ma100,
        "trend": trend,
        "volume_change": volume_change,
        "data_points": len(closes),
        "fallback_used": data.get("fallback", False),
        "sentiment_score": sentiment_score,
        "sentiment_label": sentiment_label,
        "news_count": news_count,
    }
