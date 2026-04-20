from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

async def _generate_ai_rationale(symbol: str, analysis: dict, recommendation: str) -> str:
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        from app.core.config import settings
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=0.3,
            google_api_key=settings.GEMINI_API_KEY
        )
        prompt = (
            f"Bạn là chuyên gia phân tích tài chính. Viết báo cáo ngắn gọn cho cổ phiếu {symbol} bằng tiếng Việt.\n\n"
            f"Chỉ số kỹ thuật: Giá {analysis['price']:.2f} | MA5={analysis['ma5']:.2f} | MA20={analysis['ma20']:.2f} "
            f"| Xu hướng: {analysis['trend']} | Biến động KL: {analysis.get('volume_change', 0)*100:.1f}%\n"
            f"Tâm lý thị trường: {analysis.get('sentiment_label', 'Trung lập')} "
            f"(điểm {analysis.get('sentiment_score', 0):.3f}, {analysis.get('news_count', 0)} bài báo)\n"
            f"Khuyến nghị: {recommendation}\n\n"
            f"Yêu cầu (tối đa 180 từ):\n"
            f"1. Tóm tắt tình hình thị trường (2 câu)\n"
            f"2. Rủi ro chính\n"
            f"3. Cơ hội tiềm năng\n"
            f"4. Kết luận: Tích cực / Tiêu cực / Trung lập"
        )
        response = await llm.ainvoke(prompt)
        return response.content
    except Exception as e:
        logger.warning(f"[ADVISOR] LLM rationale generation failed: {e}")
        return ""

async def get_recommendation(analysis: Dict[str, Any]):
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
            "sentiment_score": None,
            "sentiment_label": None,
            "news_count": None,
            "ai_rationale": "",
            "overall_assessment": "Trung lập",
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

    # Điều chỉnh confidence dựa trên sentiment
    sentiment_score = analysis.get("sentiment_score", 0) or 0
    if recommendation == "BUY" and sentiment_score > 0.15:
        confidence = min(confidence + 0.08, 0.95)
    elif recommendation == "SELL" and sentiment_score < -0.15:
        confidence = min(confidence + 0.08, 0.95)
    elif recommendation == "BUY" and sentiment_score < -0.15:
        confidence = max(confidence - 0.10, 0.40)
    elif recommendation == "SELL" and sentiment_score > 0.15:
        confidence = max(confidence - 0.10, 0.40)

    # Overall assessment dựa trên recommendation + sentiment
    sentiment_label = analysis.get("sentiment_label", "Trung lập") or "Trung lập"
    if recommendation == "BUY" and sentiment_label == "Tích cực":
        overall_assessment = "Tích cực"
    elif recommendation == "SELL" and sentiment_label == "Tiêu cực":
        overall_assessment = "Tiêu cực"
    elif sentiment_label != "Trung lập":
        overall_assessment = sentiment_label
    else:
        overall_assessment = "Trung lập"

    symbol = analysis.get("symbol", "")
    ai_rationale = await _generate_ai_rationale(symbol, analysis, recommendation)

    return {
        "symbol": symbol,
        "price": current_price,
        "trend": trend,
        "recommendation": recommendation,
        "confidence": confidence,
        "risk_opportunity": risk_op,
        "target_price": target_p,
        "stop_loss": stop_l,
        "investment_strategy": strategy,
        "sentiment_score": analysis.get("sentiment_score"),
        "sentiment_label": sentiment_label,
        "news_count": analysis.get("news_count"),
        "ai_rationale": ai_rationale,
        "overall_assessment": overall_assessment,
    }
