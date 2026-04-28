"""
TechnicalAnalysisService — tính chỉ báo kỹ thuật từ OHLCV data.

Input : list OHLCV dicts (mới nhất trước, format TCBS/Yahoo)
Output: dict indicators + signal tổng hợp + context string cho LLM
Chỉ dùng pandas (transitive dep của yfinance) — không cần pandas-ta.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

try:
    import pandas as pd
    _PANDAS_OK = True
except ImportError:
    _PANDAS_OK = False
    logger.error("pandas not installed — TechnicalAnalysisService disabled")


class TechnicalAnalysisService:

    MIN_BARS = 30   # cần tối thiểu để tính các chỉ báo

    # ─── Public API ───────────────────────────────────────────────────────────

    @classmethod
    def compute(cls, prices: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Tính đầy đủ chỉ báo từ list OHLCV.
        prices: descending (mới nhất ở index 0), format {date,open,high,low,close,volume}.
        Returns None nếu dữ liệu không đủ hoặc pandas thiếu.
        """
        if not _PANDAS_OK or not prices or len(prices) < cls.MIN_BARS:
            return None

        df = cls._to_df(prices)
        if df is None or len(df) < 26:
            return None

        closes  = df["close"]
        highs   = df["high"]
        lows    = df["low"]
        volumes = df["volume"]
        current = float(closes.iloc[-1])
        current_date = str(df["date"].iloc[-1]) if "date" in df.columns else ""

        rsi_s   = cls._rsi(closes, 14)
        rsi_val = cls._last(rsi_s)

        macd_line, signal_line, histogram = cls._macd(closes)
        macd_val   = cls._last(macd_line)
        signal_val = cls._last(signal_line)
        hist_val   = cls._last(histogram)
        macd_cross = cls._macd_crossover(histogram)

        bb_upper, bb_mid, bb_lower = cls._bollinger(closes, 20, 2)
        bb_u = cls._last(bb_upper)
        bb_m = cls._last(bb_mid)
        bb_l = cls._last(bb_lower)
        bb_position = cls._bb_position(current, bb_u, bb_l)

        sma = {f"sma{p}": cls._last(closes.rolling(p).mean())
               for p in [20, 50, 200] if len(closes) >= p}
        ema = {f"ema{p}": cls._last(closes.ewm(span=p, adjust=False).mean())
               for p in [9, 20] if len(closes) >= p}

        trend = cls._trend(current, sma)

        vol_avg20  = cls._last(volumes.rolling(20).mean())
        vol_cur    = float(volumes.iloc[-1])
        vol_ratio  = round(vol_cur / vol_avg20, 2) if vol_avg20 and vol_avg20 > 0 else None

        recent = df.tail(20)
        support    = round(float(lows.tail(20).min()),  2)
        resistance = round(float(highs.tail(20).max()), 2)

        signal, buy_cnt, sell_cnt = cls._composite_signal(
            rsi_val, macd_val, signal_val, macd_cross,
            bb_position, trend, vol_ratio,
        )

        return {
            "current_close": round(current, 2),
            "date":          current_date,
            "rsi":           rsi_val,
            "macd": {
                "macd":      macd_val,
                "signal":    signal_val,
                "histogram": hist_val,
                "crossover": macd_cross,
            },
            "bollinger": {
                "upper":    bb_u,
                "mid":      bb_m,
                "lower":    bb_l,
                "position": bb_position,
            },
            "sma":        sma,
            "ema":        ema,
            "trend":      trend,
            "volume": {
                "current": round(vol_cur, 0),
                "avg20":   round(vol_avg20, 0) if vol_avg20 else None,
                "ratio":   vol_ratio,
            },
            "support":     support,
            "resistance":  resistance,
            "signal":      signal,
            "buy_signals": buy_cnt,
            "sell_signals":sell_cnt,
        }

    @classmethod
    def format_for_llm(cls, ticker: str, ta: Dict[str, Any]) -> str:
        """Chuyển kết quả compute() thành context string để LLM nhận định."""
        _SIGNAL_LABELS = {
            "STRONG_BUY":  "📈 MẠNH MUA",
            "BUY":         "🟢 MUA",
            "NEUTRAL":     "⚪ TRUNG TÍNH",
            "SELL":        "🔴 BÁN",
            "STRONG_SELL": "📉 MẠNH BÁN",
        }
        _BB_POS = {
            "above_upper": "trên dải trên — vùng overbought",
            "near_upper":  "gần dải trên",
            "middle":      "giữa dải — trung tính",
            "near_lower":  "gần dải dưới",
            "below_lower": "dưới dải dưới — vùng oversold",
        }

        signal_label = _SIGNAL_LABELS.get(ta.get("signal", "NEUTRAL"), "⚪ TRUNG TÍNH")
        macd  = ta.get("macd", {})
        bb    = ta.get("bollinger", {})
        sma   = ta.get("sma", {})
        ema   = ta.get("ema", {})
        vol   = ta.get("volume", {})
        close = ta["current_close"]

        rsi = ta.get("rsi")
        rsi_note = ""
        if rsi is not None:
            if rsi < 30:   rsi_note = " ⬇️ Vùng oversold — tiềm năng hồi phục"
            elif rsi > 70: rsi_note = " ⬆️ Vùng overbought — cẩn trọng"
            else:          rsi_note = " Vùng trung tính"

        lines = [
            f"=== PHÂN TÍCH KỸ THUẬT {ticker} | {ta.get('date','')} ===",
            f"Giá hiện tại : {close:,.2f}",
            f"Tín hiệu tổng: {signal_label} (mua={ta.get('buy_signals',0)}, bán={ta.get('sell_signals',0)})",
            "",
            f"RSI(14)  : {rsi if rsi is not None else 'N/A'}{rsi_note}",
            f"MACD     : {macd.get('macd','N/A')} | Signal: {macd.get('signal','N/A')} | Hist: {macd.get('histogram','N/A')}",
        ]
        if macd.get("crossover"):
            cross_txt = "MUA — histogram vừa cắt lên" if macd["crossover"] == "BUY" else "BÁN — histogram vừa cắt xuống"
            lines.append(f"  ↳ Tín hiệu MACD: {cross_txt}")

        lines += [
            f"BB(20,2) : Upper {bb.get('upper','N/A')} | Mid {bb.get('mid','N/A')} | Lower {bb.get('lower','N/A')}",
            f"  ↳ Giá đang {_BB_POS.get(bb.get('position',''), 'N/A')}",
            "",
            "Moving Averages:",
        ]
        for k, v in sorted(sma.items()):
            if v is not None:
                pos = "trên" if close > v else "dưới"
                lines.append(f"  {k.upper()}: {v:,.2f}  (giá đang {pos})")
        for k, v in sorted(ema.items()):
            if v is not None:
                lines.append(f"  {k.upper()}: {v:,.2f}")

        vol_ratio = vol.get("ratio")
        vol_note  = f" — {'🔺 đột biến' if vol_ratio and vol_ratio > 1.5 else 'bình thường'}" if vol_ratio else ""
        lines += [
            "",
            f"Xu hướng   : {ta.get('trend','N/A')}",
            f"Hỗ trợ     : {ta.get('support','N/A'):,.2f}  |  Kháng cự: {ta.get('resistance','N/A'):,.2f}",
            f"Volume     : {vol.get('current',0):,.0f}  (TB20: {vol.get('avg20',0):,.0f}  ratio: {vol_ratio}x{vol_note})",
        ]
        return "\n".join(str(l) for l in lines)

    # ─── Indicator calculations ───────────────────────────────────────────────

    @staticmethod
    def _rsi(closes: "pd.Series", period: int = 14) -> "pd.Series":
        delta    = closes.diff()
        gain     = delta.clip(lower=0)
        loss     = -delta.clip(upper=0)
        avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
        avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
        rs = avg_gain / avg_loss.replace(0, float("nan"))
        return 100 - (100 / (1 + rs))

    @staticmethod
    def _macd(
        closes: "pd.Series", fast: int = 12, slow: int = 26, signal: int = 9
    ) -> Tuple["pd.Series", "pd.Series", "pd.Series"]:
        ema_fast    = closes.ewm(span=fast,   adjust=False).mean()
        ema_slow    = closes.ewm(span=slow,   adjust=False).mean()
        macd_line   = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        return macd_line, signal_line, macd_line - signal_line

    @staticmethod
    def _bollinger(
        closes: "pd.Series", period: int = 20, std_dev: float = 2.0
    ) -> Tuple["pd.Series", "pd.Series", "pd.Series"]:
        sma = closes.rolling(window=period).mean()
        std = closes.rolling(window=period).std()
        return sma + std_dev * std, sma, sma - std_dev * std

    # ─── Helpers ─────────────────────────────────────────────────────────────

    @staticmethod
    def _to_df(prices: List[Dict]) -> Optional["pd.DataFrame"]:
        try:
            df = pd.DataFrame(prices[::-1])   # ascending (oldest first)
            for col in ["close", "open", "high", "low"]:
                df[col] = pd.to_numeric(df[col], errors="coerce")
            df["volume"] = pd.to_numeric(df.get("volume", 0), errors="coerce").fillna(0)
            return df.dropna(subset=["close"])
        except Exception as e:
            logger.warning(f"TA _to_df error: {e}")
            return None

    @staticmethod
    def _last(series: "pd.Series") -> Optional[float]:
        try:
            val = series.iloc[-1]
            return round(float(val), 4) if pd.notna(val) else None
        except Exception:
            return None

    @staticmethod
    def _macd_crossover(histogram: "pd.Series") -> Optional[str]:
        if len(histogram) < 2:
            return None
        prev, curr = float(histogram.iloc[-2]), float(histogram.iloc[-1])
        if prev < 0 < curr:
            return "BUY"
        if prev > 0 > curr:
            return "SELL"
        return None

    @staticmethod
    def _bb_position(close: float, upper: Optional[float], lower: Optional[float]) -> Optional[str]:
        if upper is None or lower is None:
            return None
        width = upper - lower
        if width <= 0:
            return "middle"
        if close >= upper:
            return "above_upper"
        if close <= lower:
            return "below_lower"
        pct = (close - lower) / width * 100
        if pct > 70:
            return "near_upper"
        if pct < 30:
            return "near_lower"
        return "middle"

    @staticmethod
    def _trend(close: float, sma: Dict[str, Optional[float]]) -> str:
        s20 = sma.get("sma20")
        s50 = sma.get("sma50")
        if s20 and s50:
            if close > s20 > s50:
                return "UPTREND"
            if close < s20 < s50:
                return "DOWNTREND"
        return "SIDEWAYS"

    @staticmethod
    def _composite_signal(
        rsi: Optional[float],
        macd: Optional[float],
        signal: Optional[float],
        macd_cross: Optional[str],
        bb_pos: Optional[str],
        trend: str,
        vol_ratio: Optional[float],
    ) -> Tuple[str, int, int]:
        buy = sell = 0

        if rsi is not None:
            if rsi < 30:    buy  += 2
            elif rsi < 45:  buy  += 1
            elif rsi > 70:  sell += 2
            elif rsi > 55:  sell += 1

        if macd_cross == "BUY":   buy  += 2
        elif macd_cross == "SELL":sell += 2
        elif macd is not None and signal is not None:
            if macd > signal: buy  += 1
            else:             sell += 1

        if bb_pos == "below_lower": buy  += 1
        elif bb_pos == "above_upper": sell += 1

        if trend == "UPTREND":   buy  += 1
        elif trend == "DOWNTREND": sell += 1

        if vol_ratio and vol_ratio > 1.5:
            if trend == "UPTREND":   buy  += 1
            elif trend == "DOWNTREND": sell += 1

        if buy > sell + 2:    label = "STRONG_BUY"
        elif buy > sell:      label = "BUY"
        elif sell > buy + 2:  label = "STRONG_SELL"
        elif sell > buy:      label = "SELL"
        else:                 label = "NEUTRAL"

        return label, buy, sell
