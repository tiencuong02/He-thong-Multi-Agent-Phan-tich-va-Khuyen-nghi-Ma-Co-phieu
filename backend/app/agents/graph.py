import logging
from typing import Dict, Any, Optional
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, END

from app.agents.market_researcher import research_stock
from app.agents.financial_analyst import analyze_financials
from app.agents.investment_advisor import get_recommendation

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Shared state truyền qua các node trong graph
# ---------------------------------------------------------------------------
class StockState(TypedDict):
    ticker: str
    research_data: Optional[Dict[str, Any]]
    analysis_data: Optional[Dict[str, Any]]
    recommendation: Optional[Dict[str, Any]]
    error: Optional[str]


# ---------------------------------------------------------------------------
# Nodes — mỗi node là 1 agent
# ---------------------------------------------------------------------------
async def researcher_node(state: StockState) -> StockState:
    logger.info(f"[LANGGRAPH] Node 1: Market Researcher — {state['ticker']}")
    result = await research_stock(state["ticker"])
    if "error" in result:
        return {**state, "error": result["error"]}
    return {**state, "research_data": result}


def analyst_node(state: StockState) -> StockState:
    logger.info(f"[LANGGRAPH] Node 2: Financial Analyst — {state['ticker']}")
    result = analyze_financials(state["research_data"])
    if "error" in result:
        return {**state, "error": result["error"]}
    return {**state, "analysis_data": result}


def advisor_node(state: StockState) -> StockState:
    logger.info(f"[LANGGRAPH] Node 3: Investment Advisor — {state['ticker']}")
    result = get_recommendation(state["analysis_data"])
    return {**state, "recommendation": result}


# ---------------------------------------------------------------------------
# Conditional edge — dừng graph nếu có lỗi
# ---------------------------------------------------------------------------
def check_error(state: StockState) -> str:
    return "error" if state.get("error") else "ok"


# ---------------------------------------------------------------------------
# Build LangGraph
# ---------------------------------------------------------------------------
def _build_graph() -> Any:
    workflow = StateGraph(StockState)

    workflow.add_node("researcher", researcher_node)
    workflow.add_node("analyst",    analyst_node)
    workflow.add_node("advisor",    advisor_node)

    workflow.set_entry_point("researcher")

    workflow.add_conditional_edges(
        "researcher",
        check_error,
        {"ok": "analyst", "error": END}
    )
    workflow.add_conditional_edges(
        "analyst",
        check_error,
        {"ok": "advisor", "error": END}
    )
    workflow.add_edge("advisor", END)

    return workflow.compile()


_graph = _build_graph()


# ---------------------------------------------------------------------------
# Public entry point
# progress_cb: async callable(name, status, detail) — cập nhật UI real-time
# ---------------------------------------------------------------------------
async def run_analysis(ticker: str, progress_cb=None) -> Dict[str, Any]:
    ticker = ticker.upper()
    logger.info(f"--- [LANGGRAPH] Starting pipeline for {ticker} ---")

    async def _notify(name: str, status: str, detail: str = ""):
        if progress_cb:
            try:
                await progress_cb(name, status, detail)
            except Exception:
                pass  # progress update không được làm hỏng pipeline

    # ── Node 1: Market Researcher ──────────────────────────────────────────
    await _notify("Market Researcher", "running", "Đang thu thập dữ liệu giá và tin tức thị trường...")
    try:
        research_data = await research_stock(ticker)
    except Exception as e:
        await _notify("Market Researcher", "failed", str(e))
        return {"ticker": ticker, "status": "error", "error": str(e)}

    if "error" in research_data:
        await _notify("Market Researcher", "failed", research_data["error"])
        return {"ticker": ticker, "status": "error", "error": research_data["error"]}

    days = len(research_data.get("prices", []))
    news = research_data.get("metadata", {}).get("news_count", 0) or len(research_data.get("news", []))
    await _notify("Market Researcher", "completed", f"Đã thu thập {days} ngày giá · {news} tin tức")

    # ── Node 2: Financial Analyst ──────────────────────────────────────────
    await _notify("Financial Analyst", "running", "Đang tính RSI · MACD · ADX · Bollinger Bands...")
    try:
        analysis_data = analyze_financials(research_data)
    except Exception as e:
        await _notify("Financial Analyst", "failed", str(e))
        return {"ticker": ticker, "status": "error", "error": str(e)}

    if "error" in analysis_data:
        await _notify("Financial Analyst", "failed", analysis_data["error"])
        return {"ticker": ticker, "status": "error", "error": analysis_data["error"]}

    rsi  = analysis_data.get("rsi")
    macd = analysis_data.get("macd_histogram")
    adx  = analysis_data.get("adx")
    detail_fa = " · ".join(filter(None, [
        f"RSI={rsi:.1f}"       if rsi  is not None else None,
        f"MACD={macd:+.2f}"   if macd is not None else None,
        f"ADX={adx:.1f}"      if adx  is not None else None,
    ]))
    await _notify("Financial Analyst", "completed", detail_fa or "Hoàn tất tính toán chỉ số")

    # ── Node 3: Investment Advisor ─────────────────────────────────────────
    await _notify("Investment Advisor", "running", "Đang chấm điểm tín hiệu và đưa ra khuyến nghị...")
    try:
        recommendation = get_recommendation(analysis_data)
    except Exception as e:
        await _notify("Investment Advisor", "failed", str(e))
        return {"ticker": ticker, "status": "error", "error": str(e)}

    score = recommendation.get("score", 0)
    rec   = recommendation.get("recommendation", "")
    await _notify("Investment Advisor", "completed", f"Điểm {score:+d}/10 · Khuyến nghị: {rec}")

    # ── Build final_state tương thích với code cũ ──────────────────────────
    final_state = {
        "ticker":        ticker,
        "research_data": research_data,
        "analysis_data": analysis_data,
        "recommendation": recommendation,
        "error":         None,
    }

    recommendation = final_state.get("recommendation")
    analysis       = final_state.get("analysis_data")

    if not recommendation or not analysis:
        logger.error(f"[LANGGRAPH] Pipeline incomplete for {ticker}: recommendation={'set' if recommendation else 'None'}, analysis={'set' if analysis else 'None'}")
        return {"ticker": ticker, "status": "error", "error": "Pipeline did not complete successfully"}

    # Gắn metadata, price_history và agent_trace
    recommendation["fallback_used"] = analysis.get("fallback_used", False)
    recommendation["data_points"]   = analysis.get("data_points", 0)

    # Pass price history (oldest→newest) for frontend chart
    raw_prices = final_state.get("research_data", {}).get("prices", [])
    recommendation["price_history"] = list(reversed(raw_prices))
    rsi_val  = analysis.get("rsi")
    macd_val = analysis.get("macd_histogram")
    atr_val  = analysis.get("atr")
    score    = recommendation.get("score", 0)

    research     = final_state.get("research_data", {})
    meta         = research.get("metadata", {})
    data_source  = research.get("data_source", "Unknown")
    news_count   = analysis.get("news_count", 0)
    news_source  = meta.get("news_source", "none")

    if news_count and news_source == "yfinance":
        news_status = f"{news_count} tin tức (Yahoo Finance)"
    elif news_count:
        news_status = f"{news_count} tin tức (Alpha Vantage)"
    else:
        news_status = "Không có tin tức"

    recommendation["agent_trace"] = [
        {
            "agent": "Market Researcher",
            "status": "completed",
            "tools": [data_source],
            "data": f"Nguồn: {data_source} · {analysis.get('data_points', 0)} ngày · {news_status}"
        },
        {
            "agent": "Financial Analyst",
            "status": "completed",
            "logic": "MA · EMA · RSI · MACD · Bollinger · ATR",
            "data": (
                f"RSI={rsi_val:.1f}" if rsi_val is not None else "RSI=N/A"
            ) + (
                f" | MACD hist={macd_val:.4f}" if macd_val is not None else " | MACD=N/A"
            ) + (
                f" | ATR={atr_val:.2f}" if atr_val is not None else " | ATR=N/A"
            ),
            "fallback": analysis.get("fallback_used", False),
            "sentiment": analysis.get("sentiment_label", "Trung lập")
        },
        {
            "agent": "Investment Advisor",
            "status": "completed",
            "logic": f"Multi-factor scoring ({score:+d}/10)",
            "overall_assessment": recommendation.get("overall_assessment", "Trung lập")
        }
    ]

    logger.info(f"--- [LANGGRAPH] Pipeline completed for {ticker} ---")
    return recommendation
