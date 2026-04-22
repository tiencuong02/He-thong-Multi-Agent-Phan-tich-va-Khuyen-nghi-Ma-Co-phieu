from typing import Dict, Any, List, Tuple


# ---------------------------------------------------------------------------
# Helper: EMA
# ---------------------------------------------------------------------------
def _calc_ema(values: List[float], period: int) -> List[float]:
    if len(values) < period:
        return []
    k = 2 / (period + 1)
    ema = [sum(values[:period]) / period]
    for v in values[period:]:
        ema.append(v * k + ema[-1] * (1 - k))
    return ema


# ---------------------------------------------------------------------------
# RSI (14 periods)
# ---------------------------------------------------------------------------
def _calc_rsi(closes: List[float], period: int = 14) -> float | None:
    """Wilder's Smoothed RSI — dùng toàn bộ data có sẵn để smooth."""
    if len(closes) < period * 2:
        return None
    chron = list(reversed(closes))  # oldest → newest

    # Seed: avg gain/loss của period đầu tiên
    gains, losses = [], []
    for i in range(1, period + 1):
        diff = chron[i] - chron[i - 1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    # Wilder smoothing cho phần còn lại
    for i in range(period + 1, len(chron)):
        diff = chron[i] - chron[i - 1]
        avg_gain = (avg_gain * (period - 1) + max(diff, 0)) / period
        avg_loss = (avg_loss * (period - 1) + max(-diff, 0)) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)


# ---------------------------------------------------------------------------
# MACD (12/26 EMA, signal=9)
# Returns: (macd_line, signal_line, histogram) — most recent values
# ---------------------------------------------------------------------------
def _calc_macd(closes: List[float]) -> Tuple[float, float, float] | Tuple[None, None, None]:
    chron = list(reversed(closes))
    if len(chron) < 35:
        return None, None, None
    ema12 = _calc_ema(chron, 12)
    ema26 = _calc_ema(chron, 26)
    if not ema12 or not ema26:
        return None, None, None
    # Align lengths
    offset = 26 - 12  # ema26 starts 14 bars later than ema12
    macd_line = [ema12[i + offset] - ema26[i] for i in range(len(ema26))]
    if len(macd_line) < 9:
        return None, None, None
    signal_line = _calc_ema(macd_line, 9)
    if not signal_line:
        return None, None, None
    macd_val = macd_line[-1]
    signal_val = signal_line[-1]
    return round(macd_val, 4), round(signal_val, 4), round(macd_val - signal_val, 4)


# ---------------------------------------------------------------------------
# Bollinger Bands (20 periods, 2σ)
# Returns: (upper, middle, lower) — based on most recent 20 closes
# ---------------------------------------------------------------------------
def _calc_bollinger(closes: List[float], period: int = 20, std_mult: float = 2.0) -> Tuple[float, float, float] | Tuple[None, None, None]:
    if len(closes) < period:
        return None, None, None
    recent = closes[:period]
    mid = sum(recent) / period
    variance = sum((x - mid) ** 2 for x in recent) / period
    std = variance ** 0.5
    return round(mid + std_mult * std, 4), round(mid, 4), round(mid - std_mult * std, 4)


# ---------------------------------------------------------------------------
# ADX (Average Directional Index, 14 periods)
# prices: list of {high, low, close}, newest first
# Returns: (adx, plus_di, minus_di)
# ---------------------------------------------------------------------------
def _calc_adx(prices: List[Dict], period: int = 14) -> Tuple[float, float, float] | Tuple[None, None, None]:
    if len(prices) < period * 2 + 1:
        return None, None, None

    chron = list(reversed(prices))  # oldest → newest

    plus_dms, minus_dms, trs = [], [], []
    for i in range(1, len(chron)):
        high      = float(chron[i]["high"])
        low       = float(chron[i]["low"])
        prev_high = float(chron[i - 1]["high"])
        prev_low  = float(chron[i - 1]["low"])
        prev_close= float(chron[i - 1]["close"])

        up_move   = high - prev_high
        down_move = prev_low - low

        plus_dms.append(up_move   if up_move > down_move   and up_move   > 0 else 0)
        minus_dms.append(down_move if down_move > up_move  and down_move > 0 else 0)
        trs.append(max(high - low, abs(high - prev_close), abs(low - prev_close)))

    if len(trs) < period:
        return None, None, None

    # Wilder smoothing seed (sum of first period)
    s_tr    = sum(trs[:period])
    s_plus  = sum(plus_dms[:period])
    s_minus = sum(minus_dms[:period])

    def _di(s_p, s_m, s_t):
        if s_t == 0:
            return 0.0, 0.0
        return 100 * s_p / s_t, 100 * s_m / s_t

    def _dx(s_p, s_m, s_t):
        pdi, mdi = _di(s_p, s_m, s_t)
        denom = pdi + mdi
        return 100 * abs(pdi - mdi) / denom if denom else 0.0

    dx_series = [_dx(s_plus, s_minus, s_tr)]

    for i in range(period, len(trs)):
        s_tr    = s_tr    - s_tr    / period + trs[i]
        s_plus  = s_plus  - s_plus  / period + plus_dms[i]
        s_minus = s_minus - s_minus / period + minus_dms[i]
        dx_series.append(_dx(s_plus, s_minus, s_tr))

    if len(dx_series) < period:
        return None, None, None

    # ADX = Wilder smooth of DX series
    adx = sum(dx_series[:period]) / period
    for dx in dx_series[period:]:
        adx = (adx * (period - 1) + dx) / period

    plus_di, minus_di = _di(s_plus, s_minus, s_tr)
    return round(adx, 2), round(plus_di, 2), round(minus_di, 2)


# ---------------------------------------------------------------------------
# ATR (Average True Range, 14 periods)
# prices: list of {high, low, close}, newest first
# ---------------------------------------------------------------------------
def _calc_atr(prices: List[Dict], period: int = 14) -> float | None:
    if len(prices) < period + 1:
        return None
    trs = []
    for i in range(period):
        high = float(prices[i]["high"])
        low = float(prices[i]["low"])
        prev_close = float(prices[i + 1]["close"])
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        trs.append(tr)
    return round(sum(trs) / period, 4)


# ---------------------------------------------------------------------------
# Trend: đếm nến tăng/giảm liên tiếp trong 5 nến gần nhất
# closes[0] = newest
# ---------------------------------------------------------------------------
def _detect_trend(closes: List[float], window: int = 5) -> str:
    if len(closes) < window + 1:
        return "stable"
    segment = closes[:window + 1]
    ups = sum(1 for i in range(window) if segment[i] < segment[i + 1])
    downs = sum(1 for i in range(window) if segment[i] > segment[i + 1])
    if ups >= 3:
        return "up"
    if downs >= 3:
        return "down"
    return "stable"


# ---------------------------------------------------------------------------
# News sentiment aggregation
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Main analysis function
# ---------------------------------------------------------------------------
def analyze_financials(data: Dict[str, Any]):
    """
    Financial Analyst: MA, EMA, RSI, MACD, Bollinger Bands, ATR, Trend, Volume.
    """
    prices = data.get("prices", [])
    if not isinstance(prices, list) or len(prices) < 20:
        return {"error": "Insufficient price data for analysis (need at least 20 days)"}

    closes: List[float] = [float(p["close"]) for p in prices]
    volumes: List[int] = [int(p["volume"]) for p in prices]

    # --- Moving Averages (SMA) ---
    ma5  = sum(closes[:5]) / 5
    ma20 = sum(closes[:20]) / 20
    ma50  = sum(closes[:50]) / 50  if len(closes) >= 50  else None
    ma100 = sum(closes[:100]) / 100 if len(closes) >= 100 else None

    # --- EMA ---
    ema12_series = _calc_ema(list(reversed(closes)), 12)
    ema26_series = _calc_ema(list(reversed(closes)), 26)
    ema12 = round(ema12_series[-1], 4) if ema12_series else None
    ema26 = round(ema26_series[-1], 4) if ema26_series else None

    # --- RSI ---
    rsi = _calc_rsi(closes, 14)

    # --- MACD ---
    macd_line, macd_signal, macd_hist = _calc_macd(closes)

    # --- Bollinger Bands ---
    bb_upper, bb_mid, bb_lower = _calc_bollinger(closes, 20)

    # --- ATR ---
    atr = _calc_atr(prices, 14)

    # --- ADX ---
    adx, plus_di, minus_di = _calc_adx(prices, 14)

    # --- Trend (multi-candle) ---
    trend = _detect_trend(closes, 5)

    # --- Volume ---
    curr_volume = volumes[0]
    avg_volume_5 = sum(volumes[1:6]) / 5
    volume_change = (curr_volume - avg_volume_5) / avg_volume_5 if avg_volume_5 > 0 else 0

    # --- Sentiment ---
    news = data.get("news", [])
    sentiment_score, sentiment_label, news_count = _aggregate_news_sentiment(news)

    curr_price = closes[0]

    return {
        "symbol":         data.get("symbol"),
        "price":          curr_price,
        # SMA
        "ma5":            round(ma5, 4),
        "ma20":           round(ma20, 4),
        "ma50":           round(ma50, 4) if ma50 else None,
        "ma100":          round(ma100, 4) if ma100 else None,
        # EMA
        "ema12":          ema12,
        "ema26":          ema26,
        # Momentum
        "rsi":            rsi,
        "macd_line":      macd_line,
        "macd_signal":    macd_signal,
        "macd_histogram": macd_hist,
        # Volatility
        "bb_upper":       bb_upper,
        "bb_mid":         bb_mid,
        "bb_lower":       bb_lower,
        "atr":            atr,
        # Price action
        "trend":          trend,
        "volume_change":  round(volume_change, 4),
        # ADX
        "adx":            adx,
        "plus_di":        plus_di,
        "minus_di":       minus_di,
        # Meta
        "data_points":    len(closes),
        "fallback_used":  data.get("fallback", False),
        # Sentiment
        "sentiment_score": sentiment_score,
        "sentiment_label": sentiment_label,
        "news_count":      news_count,
    }
