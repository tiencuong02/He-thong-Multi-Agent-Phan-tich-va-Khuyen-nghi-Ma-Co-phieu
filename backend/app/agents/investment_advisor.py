from typing import Dict, Any


# ---------------------------------------------------------------------------
# Multi-factor scoring
# Score range: -10 → +10
# BUY if score >= +4, SELL if score <= -4, HOLD otherwise
# ---------------------------------------------------------------------------
def _compute_score(analysis: dict) -> tuple[int, list[str]]:
    """Returns (score, list of signal descriptions)."""
    score = 0
    signals = []

    price  = analysis.get("price", 0)
    ma5    = analysis.get("ma5", 0)
    ma20   = analysis.get("ma20", 0)
    rsi    = analysis.get("rsi")
    macd_line   = analysis.get("macd_line")
    macd_signal = analysis.get("macd_signal")
    bb_upper = analysis.get("bb_upper")
    bb_lower = analysis.get("bb_lower")
    volume_change = analysis.get("volume_change", 0)
    trend  = analysis.get("trend", "stable")
    sentiment_score = analysis.get("sentiment_score", 0) or 0

    # 1. MA Crossover (±2)
    if ma5 and ma20:
        if ma5 > ma20:
            score += 2
            signals.append(f"Đường trung bình ngắn hạn ({ma5:.2f}) vượt lên trên đường trung bình dài hạn ({ma20:.2f}) — Tín hiệu tăng giá (+2)")
        elif ma5 < ma20:
            score -= 2
            signals.append(f"Đường trung bình ngắn hạn ({ma5:.2f}) nằm dưới đường trung bình dài hạn ({ma20:.2f}) — Tín hiệu giảm giá (-2)")

    # 2. RSI (±2)
    # Vùng 40-70: momentum bình thường, không phạt
    if rsi is not None:
        if rsi < 30:
            score += 2
            signals.append(f"Sức mua/bán: {rsi:.1f}/100 — Giá đang ở vùng bán quá mức, có thể sớm phục hồi (+2)")
        elif rsi < 40:
            score += 1
            signals.append(f"Sức mua/bán: {rsi:.1f}/100 — Lực mua đang yếu, tiềm năng phục hồi (+1)")
        elif rsi > 80:
            score -= 2
            signals.append(f"Sức mua/bán: {rsi:.1f}/100 — Giá đang ở vùng mua quá mức cực đoan, rủi ro điều chỉnh cao (-2)")
        elif rsi > 70:
            score -= 1
            signals.append(f"Sức mua/bán: {rsi:.1f}/100 — Giá tiếp cận vùng mua quá mức, cần theo dõi (-1)")

    # 3. MACD crossover (±2)
    if macd_line is not None and macd_signal is not None:
        if macd_line > macd_signal:
            score += 2
            signals.append("Đà tăng giá đang chiếm ưu thế — Động lượng thị trường đang tích cực (+2)")
        else:
            score -= 2
            signals.append("Đà giảm giá đang chiếm ưu thế — Động lượng thị trường đang tiêu cực (-2)")

    # 4. Bollinger Bands (±1)
    if bb_upper is not None and bb_lower is not None and price:
        band_width = bb_upper - bb_lower
        if band_width > 0:
            position = (price - bb_lower) / band_width  # 0=lower, 1=upper
            if position < 0.2:
                score += 1
                signals.append(f"Giá đang tiếp cận vùng đáy dao động ({bb_lower:.2f}) — Khả năng bật tăng trở lại (+1)")
            elif position > 0.8:
                score -= 1
                signals.append(f"Giá đang tiếp cận vùng đỉnh dao động ({bb_upper:.2f}) — Rủi ro điều chỉnh giá (-1)")

    # 5. Volume confirmation (±1)
    if volume_change > 0.3 and trend == "up":
        score += 1
        signals.append(f"Khối lượng giao dịch tăng {volume_change*100:.1f}% trong phiên tăng giá — Xu hướng được xác nhận mạnh (+1)")
    elif volume_change > 0.3 and trend == "down":
        score -= 1
        signals.append(f"Khối lượng giao dịch tăng {volume_change*100:.1f}% trong phiên giảm giá — Áp lực bán đang rất mạnh (-1)")

    # 6. Trend multi-candle (±1)
    if trend == "up":
        score += 1
        signals.append("Giá đóng cửa tăng liên tục trong 5 phiên gần nhất — Xu hướng tăng ngắn hạn rõ ràng (+1)")
    elif trend == "down":
        score -= 1
        signals.append("Giá đóng cửa giảm liên tục trong 5 phiên gần nhất — Xu hướng giảm ngắn hạn rõ ràng (-1)")

    # 7. Sentiment (±1)
    if sentiment_score > 0.15:
        score += 1
        signals.append(f"Tin tức thị trường đang nghiêng về chiều tích cực (mức độ: {sentiment_score:.2f}) (+1)")
    elif sentiment_score < -0.15:
        score -= 1
        signals.append(f"Tin tức thị trường đang nghiêng về chiều tiêu cực (mức độ: {sentiment_score:.2f}) (-1)")

    # 8. ADX — độ mạnh xu hướng (±2)
    adx      = analysis.get("adx")
    plus_di  = analysis.get("plus_di")
    minus_di = analysis.get("minus_di")

    if adx is not None:
        if adx < 20:
            signals.append(f"Thị trường đang đi ngang, chưa có xu hướng rõ (ADX={adx:.1f}) — các tín hiệu kém tin cậy hơn")
        elif adx >= 40 and plus_di is not None and minus_di is not None:
            if plus_di > minus_di:
                score += 2
                signals.append(f"Xu hướng tăng rất mạnh được xác nhận (ADX={adx:.1f}) (+2)")
            else:
                score -= 2
                signals.append(f"Xu hướng giảm rất mạnh được xác nhận (ADX={adx:.1f}) (-2)")
        elif adx >= 25 and plus_di is not None and minus_di is not None:
            if plus_di > minus_di:
                score += 1
                signals.append(f"Xu hướng tăng được xác nhận (ADX={adx:.1f}, lực tăng > lực giảm) (+1)")
            else:
                score -= 1
                signals.append(f"Xu hướng giảm được xác nhận (ADX={adx:.1f}, lực giảm > lực tăng) (-1)")

    return score, signals, adx


# ---------------------------------------------------------------------------
# Dynamic Target & Stop Loss dựa theo ATR
# ---------------------------------------------------------------------------
def _calc_targets(price: float, atr: float | None, recommendation: str) -> tuple[float, float]:
    if atr and atr > 0:
        if recommendation == "BUY":
            return round(price + 2.0 * atr, 2), round(price - 1.0 * atr, 2)
        elif recommendation == "SELL":
            return round(price - 2.0 * atr, 2), round(price + 1.0 * atr, 2)
    # Fallback nếu không có ATR
    if recommendation == "BUY":
        return round(price * 1.08, 2), round(price * 0.95, 2)
    elif recommendation == "SELL":
        return round(price * 0.92, 2), round(price * 1.05, 2)
    return round(price * 1.05, 2), round(price * 0.97, 2)




# ---------------------------------------------------------------------------
# Markdown report builder
# ---------------------------------------------------------------------------
def _build_risk_report(analysis: dict, score: int, signals: list) -> str:
    rsi     = analysis.get("rsi")
    macd_h  = analysis.get("macd_histogram")
    bb_u    = analysis.get("bb_upper")
    bb_l    = analysis.get("bb_lower")
    atr     = analysis.get("atr")
    vol     = analysis.get("volume_change", 0)

    lines = ["**Chỉ số kỹ thuật**\n"]

    if rsi is not None:
        if rsi > 70:
            rsi_note = "Vùng mua quá mức — dễ xảy ra điều chỉnh 🔴"
        elif rsi < 30:
            rsi_note = "Vùng bán quá mức — có thể sắp phục hồi 🟢"
        else:
            rsi_note = "Vùng trung lập — chưa có tín hiệu rõ 🟡"
        lines.append(f"- **Sức mua/bán ({rsi:.1f}/100):** {rsi_note}")

    if macd_h is not None:
        macd_note = "Đà tăng đang tích cực 🟢" if macd_h > 0 else "Đà giảm đang chiếm ưu thế 🔴"
        lines.append(f"- **Động lượng thị trường ({macd_h:+.2f}):** {macd_note}")

    if bb_u is not None and bb_l is not None:
        lines.append(f"- **Vùng dao động giá:** {bb_l:.2f} (đáy) – {bb_u:.2f} (đỉnh)")

    if atr is not None:
        lines.append(f"- **Biên độ biến động bình quân:** ±{atr:.2f} mỗi phiên")

    adx_val      = analysis.get("adx")
    plus_di_val  = analysis.get("plus_di")
    minus_di_val = analysis.get("minus_di")
    if adx_val is not None:
        if adx_val < 20:
            adx_note = "Không có xu hướng (sideway) ⚪"
        elif adx_val < 25:
            adx_note = "Xu hướng đang hình thành 🟡"
        elif adx_val < 40:
            adx_note = "Xu hướng rõ ràng 🟢"
        else:
            adx_note = "Xu hướng rất mạnh 🔵"
        di_str = f" | Lực tăng {plus_di_val:.1f} / Lực giảm {minus_di_val:.1f}" if plus_di_val is not None else ""
        lines.append(f"- **Độ mạnh xu hướng ({adx_val:.1f}/100):** {adx_note}{di_str}")

    vol_note = "cao hơn" if vol > 0 else "thấp hơn"
    lines.append(f"- **Khối lượng giao dịch:** {abs(vol * 100):.1f}% {vol_note} trung bình 5 phiên")

    lines.append(f"\n**Tín hiệu phân tích** *(Điểm tổng hợp: {score:+d}/10)*\n")
    for s in signals:
        emoji = "✅" if "(+" in s else "⚠️"
        lines.append(f"{emoji} {s}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main recommendation function
# ---------------------------------------------------------------------------
def get_recommendation(analysis: Dict[str, Any]):
    if "error" in analysis:
        return {
            "symbol":            analysis.get("symbol", "N/A"),
            "price":             0,
            "trend":             "unknown",
            "recommendation":    "ERROR",
            "confidence":        0,
            "risk_opportunity":  f"Error: {analysis['error']}",
            "sentiment_score":   None,
            "sentiment_label":   None,
            "news_count":        None,
            "ai_rationale":      "",
            "overall_assessment": "Trung lập",
            "error":             analysis["error"]
        }

    price = analysis.get("price", 0)
    atr   = analysis.get("atr")
    trend = analysis.get("trend", "stable")

    # --- Scoring ---
    score, signals, adx = _compute_score(analysis)

    # --- Decision ---
    if score >= 4:
        recommendation = "BUY"
    elif score <= -4:
        recommendation = "SELL"
    else:
        recommendation = "HOLD"

    # --- Confidence ---
    # 1. Signal agreement: tỷ lệ tín hiệu đồng thuận với quyết định
    n_pos = sum(1 for s in signals if "(+" in s)
    n_neg = sum(1 for s in signals if "(-" in s)
    n_total = n_pos + n_neg

    if n_total > 0:
        if recommendation == "BUY":
            agreement = n_pos / n_total
        elif recommendation == "SELL":
            agreement = n_neg / n_total
        else:
            # HOLD: độ đồng thuận cao khi tín hiệu cân bằng
            agreement = 1.0 - abs(n_pos - n_neg) / n_total
    else:
        agreement = 0.5

    # 2. Score magnitude: độ mạnh của quyết định (max score = 12)
    magnitude = abs(score) / 12

    # 3. Blend: 60% đồng thuận tín hiệu + 40% độ mạnh điểm số
    base = agreement * 0.6 + magnitude * 0.4

    # 4. ADX multiplier — dải thay vì flat penalty
    if adx is None:
        adx_mult = 0.80          # không có dữ liệu → thận trọng
    elif adx < 20:
        adx_mult = 0.65          # sideway, tín hiệu kém tin cậy
    elif adx < 25:
        adx_mult = 0.85          # xu hướng đang hình thành
    elif adx < 40:
        adx_mult = 1.00          # xu hướng rõ ràng
    else:
        adx_mult = 0.95          # quá mạnh, dễ đảo chiều

    # 5. Volume confirmation — boost nhẹ khi khối lượng xác nhận trend
    volume_change = analysis.get("volume_change", 0) or 0
    if abs(volume_change) > 0.2:
        vol_mult = 1.05
    else:
        vol_mult = 1.00

    confidence = round(min(base * adx_mult * vol_mult, 0.85), 2)
    confidence = max(confidence, 0.20)   # sàn 20% — không khuyến nghị nếu quá thấp

    # --- Dynamic Target / Stop Loss ---
    target_price, stop_loss = _calc_targets(price, atr, recommendation)

    # --- Investment strategy text ---
    score_label = f"Điểm tổng hợp: {score:+d}/10"
    if recommendation == "BUY":
        strategy = (
            f"Tín hiệu kỹ thuật nghiêng về tăng ({score_label}). "
            f"Cân nhắc mở vị thế mua quanh {price:.2f}. "
            f"Mục tiêu {target_price:.2f} (+{((target_price/price)-1)*100:.1f}%), "
            f"cắt lỗ tại {stop_loss:.2f} (-{(1-(stop_loss/price))*100:.1f}%)."
        )
    elif recommendation == "SELL":
        strategy = (
            f"Tín hiệu kỹ thuật nghiêng về giảm ({score_label}). "
            f"Cân nhắc thoát vị thế hoặc bán khống quanh {price:.2f}. "
            f"Vùng mục tiêu {target_price:.2f}, "
            f"dừng lỗ tại {stop_loss:.2f}."
        )
    else:
        strategy = (
            f"Tín hiệu kỹ thuật trung lập ({score_label}). "
            f"Thị trường chưa có xu hướng rõ ràng — quan sát và chờ breakout "
            f"trên {target_price:.2f} hoặc breakdown dưới {stop_loss:.2f}."
        )

    # --- risk_opportunity: markdown sạch, dễ đọc ---
    risk_op = _build_risk_report(analysis, score, signals)

    # --- Overall assessment ---
    sentiment_label = analysis.get("sentiment_label", "Trung lập") or "Trung lập"
    if recommendation == "BUY" and sentiment_label == "Tích cực":
        overall_assessment = "Tích cực"
    elif recommendation == "SELL" and sentiment_label == "Tiêu cực":
        overall_assessment = "Tiêu cực"
    elif recommendation == "BUY" and score >= 6:
        overall_assessment = "Tích cực"
    elif recommendation == "SELL" and score <= -6:
        overall_assessment = "Tiêu cực"
    elif sentiment_label != "Trung lập":
        # Sentiment là tiebreaker chỉ khi kỹ thuật thực sự trung lập (-2 đến +2).
        # Nếu kỹ thuật đã nghiêng rõ một chiều (|score| > 2), tín hiệu xung đột → Mixed.
        if sentiment_label == "Tích cực" and score < -2:
            overall_assessment = "Trung lập"   # kỹ thuật rõ âm, tin tức tốt → mixed
        elif sentiment_label == "Tiêu cực" and score > 2:
            overall_assessment = "Trung lập"   # kỹ thuật rõ dương, tin tức xấu → mixed
        else:
            overall_assessment = sentiment_label  # score nhẹ → sentiment tipping point
    else:
        overall_assessment = "Trung lập"

    symbol = analysis.get("symbol", "")

    return {
        "symbol":              symbol,
        "price":               price,
        "trend":               trend,
        "recommendation":      recommendation,
        "confidence":          confidence,
        "score":               score,
        "risk_opportunity":    risk_op,
        "target_price":        target_price,
        "stop_loss":           stop_loss,
        "investment_strategy": strategy,
        "sentiment_score":     analysis.get("sentiment_score"),
        "sentiment_label":     sentiment_label,
        "news_count":          analysis.get("news_count"),
        "overall_assessment":  overall_assessment,
        "rsi":                 analysis.get("rsi"),
        "macd_histogram":      analysis.get("macd_histogram"),
        "atr":                 atr,
        "adx":                 analysis.get("adx"),
        "plus_di":             analysis.get("plus_di"),
        "minus_di":            analysis.get("minus_di"),
        "bb_upper":            analysis.get("bb_upper"),
        "bb_lower":            analysis.get("bb_lower"),
        "volume_change":       analysis.get("volume_change", 0),
        "signals":             signals,
    }
