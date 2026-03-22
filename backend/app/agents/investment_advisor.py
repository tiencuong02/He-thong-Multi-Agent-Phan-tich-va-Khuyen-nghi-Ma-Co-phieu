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
            "risk_opportunity": f"Error: {analysis['error']}",
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
    
    risk_op = f"MA5: {ma5:.2f}, MA20: {ma20:.2f}. Volume Change: {analysis.get('volume_change', 0)*100:.1f}%."
    
    return {
        "symbol": analysis.get("symbol"),
        "price": analysis.get("price"),
        "trend": trend,
        "recommendation": recommendation,
        "confidence": confidence,
        "risk_opportunity": risk_op
    }
