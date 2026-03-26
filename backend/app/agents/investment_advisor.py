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
    
    current_price = analysis.get("price", 0)
    
    # Simple Volatility Proxy (High-Low avg of recent days could be better, 
    # but we'll use a standard percentage-based approach for now)
    volatility_factor = 0.05 # 5% base volatility
    
    if ma5 > ma20 and trend == "up":
        recommendation = "BUY"
        confidence = 0.82
        target_p = current_price * 1.10 # +10%
        stop_l = current_price * 0.95   # -5%
        strategy = f"Mở vị thế mua quanh vùng {current_price:.2f}. Kỳ vọng sóng tăng trung hạn với mục tiêu {target_p:.2f}."
    elif ma5 < ma20 and trend == "down":
        recommendation = "SELL"
        confidence = 0.78
        target_p = current_price * 0.90 # -10% target for short/exit
        stop_l = current_price * 1.05   # +5% 
        strategy = f"Thoát vị thế để bảo vệ vốn. Vùng cản mạnh tại {stop_l:.2f}. Có thể cân nhắc mua lại khi giá về vùng {target_p:.2f}."
    else:
        recommendation = "HOLD"
        confidence = 0.5
        target_p = current_price * 1.05
        stop_l = current_price * 0.97
        strategy = "Thị trường đang đi ngang hoặc có tín hiệu trái chiều. Tạm thời quan sát và chờ đợi điểm phá vỡ (Breakout)."
    
    risk_op = f"MA5: {ma5:.2f}, MA20: {ma20:.2f}. Biến động khối lượng: {analysis.get('volume_change', 0)*100:.1f}%."
    
    return {
        "symbol": analysis.get("symbol"),
        "price": current_price,
        "trend": trend,
        "recommendation": recommendation,
        "confidence": confidence,
        "risk_opportunity": risk_op,
        "target_price": target_p,
        "stop_loss": stop_l,
        "investment_strategy": strategy
    }
