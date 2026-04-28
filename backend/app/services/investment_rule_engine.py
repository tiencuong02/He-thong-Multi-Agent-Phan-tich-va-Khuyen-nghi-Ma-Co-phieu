"""
InvestmentRuleEngine — Deterministic BUY/SELL/HOLD rule engine.

Single Source of Truth cho mọi khuyến nghị đầu tư trong hệ thống.
Cả chatbot lẫn UI Dashboard đều phải dùng TechnicalAnchor từ đây —
LLM chỉ được phép GIẢI THÍCH, không được tự tạo khuyến nghị.

Scoring model:
  RSI            +2/-2  (oversold/overbought)
  MACD crossover +2/-2  (golden/death cross)
  SMA trend      +2/-2  (price > SMA20 > SMA50 / ngược lại)
  BB position    +1/-1  (below lower / above upper)
  Volume spike   +1/-1  (amplify current direction)
  Max possible:  ±8

  score ≥  4 → BUY  STRONG
  score ≥  2 → BUY  MODERATE
  score ≤ -4 → SELL STRONG
  score ≤ -2 → SELL MODERATE
  else       → HOLD
"""

import logging
from dataclasses import dataclass
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class TechnicalAnchor:
    ticker: str
    recommendation: str   # BUY | SELL | HOLD
    strength: str         # STRONG | MODERATE | WEAK
    stop_loss: float
    take_profit: float
    current_price: float
    score: int            # net score (positive = bullish)
    reason: str           # tóm tắt tín hiệu chính


class InvestmentRuleEngine:

    # ─── Public API ───────────────────────────────────────────────────────────

    @classmethod
    def compute_anchor(cls, ticker: str, ta: Dict[str, Any]) -> TechnicalAnchor:
        """
        Tính TechnicalAnchor từ output của TechnicalAnalysisService.compute().
        Hoàn toàn deterministic — không có random, không có LLM.
        """
        price      = float(ta.get("current_close", 0))
        rsi        = ta.get("rsi")
        macd_data  = ta.get("macd", {})
        bb_data    = ta.get("bollinger", {})
        sma        = ta.get("sma", {})
        vol        = ta.get("volume", {})
        support    = float(ta.get("support", price * 0.95))
        resistance = float(ta.get("resistance", price * 1.10))

        score   = 0
        reasons = []

        # ── RSI ──────────────────────────────────────────────────────────────
        if rsi is not None:
            if rsi < 30:
                score += 2
                reasons.append(f"RSI={rsi:.1f} oversold")
            elif rsi < 45:
                score += 1
                reasons.append(f"RSI={rsi:.1f} dưới trung tính")
            elif rsi > 70:
                score -= 2
                reasons.append(f"RSI={rsi:.1f} overbought")
            elif rsi > 55:
                score -= 1
                reasons.append(f"RSI={rsi:.1f} trên trung tính")

        # ── MACD ─────────────────────────────────────────────────────────────
        macd_cross = macd_data.get("crossover")
        hist       = float(macd_data.get("histogram") or 0)
        if macd_cross == "BUY":
            score += 2
            reasons.append("MACD golden cross")
        elif macd_cross == "SELL":
            score -= 2
            reasons.append("MACD death cross")
        elif hist > 0:
            score += 1
            reasons.append("MACD histogram dương")
        elif hist < 0:
            score -= 1
            reasons.append("MACD histogram âm")

        # ── SMA Trend ─────────────────────────────────────────────────────────
        sma20 = sma.get("sma20")
        sma50 = sma.get("sma50")
        if sma20 and sma50:
            if price > sma20 > sma50:
                score += 2
                reasons.append("giá > SMA20 > SMA50 (uptrend)")
            elif price < sma20 < sma50:
                score -= 2
                reasons.append("giá < SMA20 < SMA50 (downtrend)")
            elif price > sma20:
                score += 1
                reasons.append("giá > SMA20")
            elif price < sma20:
                score -= 1
                reasons.append("giá < SMA20")
        elif sma20:
            if price > sma20:
                score += 1
            elif price < sma20:
                score -= 1

        # ── Bollinger Band ────────────────────────────────────────────────────
        bb_pos = bb_data.get("position", "")
        if bb_pos == "below_lower":
            score += 1
            reasons.append("giá dưới BB lower (oversold)")
        elif bb_pos == "above_upper":
            score -= 1
            reasons.append("giá trên BB upper (overbought)")

        # ── Volume amplification ──────────────────────────────────────────────
        vol_ratio = vol.get("ratio")
        if vol_ratio and vol_ratio > 1.5:
            if score > 0:
                score += 1
                reasons.append(f"volume đột biến {vol_ratio:.1f}x (xác nhận tăng)")
            elif score < 0:
                score -= 1
                reasons.append(f"volume đột biến {vol_ratio:.1f}x (xác nhận giảm)")

        # ── Map score → recommendation ────────────────────────────────────────
        if score >= 4:
            rec, strength = "BUY", "STRONG"
        elif score >= 2:
            rec, strength = "BUY", "MODERATE"
        elif score <= -4:
            rec, strength = "SELL", "STRONG"
        elif score <= -2:
            rec, strength = "SELL", "MODERATE"
        elif score == 0:
            rec, strength = "HOLD", "MODERATE"
        else:
            rec, strength = "HOLD", "WEAK"

        # ── Stop loss & Take profit ───────────────────────────────────────────
        if rec == "BUY":
            stop_loss   = max(support,    price * 0.93)   # support hoặc -7%
            take_profit = min(resistance, price * 1.15)   # resistance hoặc +15%
        elif rec == "SELL":
            stop_loss   = min(resistance, price * 1.05)   # resistance hoặc +5%
            take_profit = max(support,    price * 0.90)   # support hoặc -10%
        else:  # HOLD
            stop_loss   = max(support,    price * 0.95)
            take_profit = min(resistance, price * 1.08)

        anchor = TechnicalAnchor(
            ticker        = ticker.upper(),
            recommendation= rec,
            strength      = strength,
            stop_loss     = round(stop_loss, 2),
            take_profit   = round(take_profit, 2),
            current_price = round(price, 2),
            score         = score,
            reason        = " | ".join(reasons) if reasons else "Không đủ tín hiệu rõ ràng",
        )
        logger.info(
            f"TechnicalAnchor {ticker}: {rec} {strength} "
            f"(score={score:+d}) SL={anchor.stop_loss} TP={anchor.take_profit}"
        )
        return anchor

    # ─── Formatting ──────────────────────────────────────────────────────────

    _REC_LABELS = {
        ("BUY",  "STRONG"):   "📈 MUA MẠNH",
        ("BUY",  "MODERATE"): "🟢 MUA",
        ("HOLD", "MODERATE"): "⚪ GIỮ",
        ("HOLD", "WEAK"):     "⚪ THEO DÕI",
        ("SELL", "MODERATE"): "🔴 BÁN",
        ("SELL", "STRONG"):   "📉 BÁN MẠNH",
    }

    @classmethod
    def format_for_llm(cls, anchor: TechnicalAnchor) -> str:
        """
        Format anchor thành chuỗi inject vào system prompt.
        LLM BẮT BUỘC sử dụng nguyên văn — không được thay đổi recommendation.
        """
        label = cls._REC_LABELS.get(
            (anchor.recommendation, anchor.strength), anchor.recommendation
        )
        return (
            "=== TECHNICAL ANCHOR — BẮT BUỘC DÙNG NGUYÊN VĂN ===\n"
            f"Mã cổ phiếu : {anchor.ticker}\n"
            f"Khuyến nghị : {label}\n"
            f"Giá hiện tại: {anchor.current_price:,.2f}\n"
            f"Cắt lỗ      : {anchor.stop_loss:,.2f}\n"
            f"Chốt lời    : {anchor.take_profit:,.2f}\n"
            f"Điểm kỹ thuật: {anchor.score:+d}/8\n"
            f"Tín hiệu    : {anchor.reason}\n"
            "=== END ANCHOR ==="
        )

    @classmethod
    def format_for_ui(cls, anchor: TechnicalAnchor) -> Dict[str, Any]:
        """Format anchor cho UI Dashboard response."""
        return {
            "ticker":         anchor.ticker,
            "recommendation": anchor.recommendation,
            "strength":       anchor.strength,
            "label":          cls._REC_LABELS.get(
                                  (anchor.recommendation, anchor.strength),
                                  anchor.recommendation
                              ),
            "stop_loss":      anchor.stop_loss,
            "take_profit":    anchor.take_profit,
            "current_price":  anchor.current_price,
            "score":          anchor.score,
            "reason":         anchor.reason,
        }
