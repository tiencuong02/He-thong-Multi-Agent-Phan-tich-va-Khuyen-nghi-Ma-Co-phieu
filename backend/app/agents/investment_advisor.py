from typing import Dict, Any

def get_recommendation(analysis: Dict[str, Any]):
    """
    Investment Advisor: Rule-based recommendation.
    IF MA5 > MA20 AND trend == "up" → BUY
    IF MA5 < MA20 AND trend == "down" → SELL
    ELSE → HOLD
    """
    if "error" in analysis:
        return {
            "symbol": analysis.get("symbol", "N/A"),
            "price": 0,
            "trend": "unknown",
            "recommendation": "ERROR",
            "confidence": 0,
            "error": analysis["error"]
        }

    ma5 = analysis.get("ma5", 0)
    ma20 = analysis.get("ma20", 0)
    trend = analysis.get("trend", "stable")
    
    recommendation = "HOLD"
    confidence = 0.5

    if ma5 > ma20 and trend == "up":
        recommendation = "BUY"
        confidence = 0.82
    elif ma5 < ma20 and trend == "down":
        recommendation = "SELL"
        confidence = 0.78
    
    return {
        "symbol": analysis.get("symbol"),
        "price": analysis.get("price"),
        "trend": trend,
        "recommendation": recommendation,
        "confidence": confidence
    }
