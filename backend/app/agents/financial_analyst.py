from typing import Dict, Any, List

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
    
    # Trend: simplistic current vs previous price
    curr_price = closes[0]
    prev_price = closes[1]
    trend = "up" if curr_price > prev_price else "down"

    # Volume change: current vs avg of last 5
    curr_volume = volumes[0]
    avg_volume_5 = sum(volumes[1:6]) / 5
    volume_change = (curr_volume - avg_volume_5) / avg_volume_5 if avg_volume_5 > 0 else 0

    return {
        "symbol": data.get("symbol"),
        "price": curr_price,
        "ma5": ma5,
        "ma20": ma20,
        "trend": trend,
        "volume_change": volume_change
    }
