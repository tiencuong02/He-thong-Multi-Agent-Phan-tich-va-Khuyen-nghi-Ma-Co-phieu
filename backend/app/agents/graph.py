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
# progress_cb được truyền qua state để các node có thể notify UI real-time
# ---------------------------------------------------------------------------
class StockState(TypedDict):
    ticker: str
    research_data: Optional[Dict[str, Any]]
    analysis_data: Optional[Dict[str, Any]]
    recommendation: Optional[Dict[str, Any]]
    error: Optional[str]
    progress_cb: Optional[Any]  # async callable(name, status, detail)


# ---------------------------------------------------------------------------
# Nodes — mỗi node là 1 agent, tự notify progress qua state["progress_cb"]
# ---------------------------------------------------------------------------
async def researcher_node(state: StockState) -> StockState:
    logger.info(f"[LANGGRAPH] Node 1: Market Researcher — {state['ticker']}")
    cb = state.get("progress_cb")

    if cb:
        try:
            await cb("Market Researcher", "running", "Đang thu thập dữ liệu giá và tin tức thị trường...")
        except Exception:
            pass

    try:
        result = await research_stock(state["ticker"])
    except Exception as e:
        if cb:
            try:
                await cb("Market Researcher", "failed", str(e))
            except Exception:
                pass
        return {**state, "error": str(e)}

    if "error" in result:
        if cb:
            try:
                await cb("Market Researcher", "failed", result["error"])
            except Exception:
                pass
        return {**state, "error": result["error"]}

    days = len(result.get("prices", []))
    news = result.get("metadata", {}).get("news_count", 0) or len(result.get("news", []))
    if cb:
        try:
            await cb("Market Researcher", "completed", f"Đã thu thập {days} ngày giá · {news} tin tức")
        except Exception:
            pass

    return {**state, "research_data": result}


async def analyst_node(state: StockState) -> StockState:
    logger.info(f"[LANGGRAPH] Node 2: Financial Analyst — {state['ticker']}")
    cb = state.get("progress_cb")

    if cb:
        try:
            await cb("Financial Analyst", "running", "Đang tính RSI · MACD · ADX · Bollinger Bands...")
        except Exception:
            pass

    try:
        result = analyze_financials(state["research_data"])
    except Exception as e:
        if cb:
            try:
                await cb("Financial Analyst", "failed", str(e))
            except Exception:
                pass
        return {**state, "error": str(e)}

    if "error" in result:
        if cb:
            try:
                await cb("Financial Analyst", "failed", result["error"])
            except Exception:
                pass
        return {**state, "error": result["error"]}

    rsi  = result.get("rsi")
    macd = result.get("macd_histogram")
    adx  = result.get("adx")
    detail = " · ".join(filter(None, [
        f"RSI={rsi:.1f}"     if rsi  is not None else None,
        f"MACD={macd:+.2f}" if macd is not None else None,
        f"ADX={adx:.1f}"    if adx  is not None else None,
    ]))
    if cb:
        try:
            await cb("Financial Analyst", "completed", detail or "Hoàn tất tính toán chỉ số")
        except Exception:
            pass

    return {**state, "analysis_data": result}


async def advisor_node(state: StockState) -> StockState:
    logger.info(f"[LANGGRAPH] Node 3: Investment Advisor — {state['ticker']}")
    cb = state.get("progress_cb")

    if cb:
        try:
            await cb("Investment Advisor", "running", "Đang chấm điểm tín hiệu và đưa ra khuyến nghị...")
        except Exception:
            pass

    try:
        result = get_recommendation(state["analysis_data"])
    except Exception as e:
        if cb:
            try:
                await cb("Investment Advisor", "failed", str(e))
            except Exception:
                pass
        return {**state, "error": str(e)}

    score = result.get("score", 0)
    rec   = result.get("recommendation", "")
    if cb:
        try:
            await cb("Investment Advisor", "completed", f"Điểm {score:+d}/10 · Khuyến nghị: {rec}")
        except Exception:
            pass

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
# Public entry point — chạy pipeline qua LangGraph compiled graph (_graph)
# progress_cb: async callable(name, status, detail) — truyền qua StockState
# ---------------------------------------------------------------------------
async def run_analysis(ticker: str, progress_cb=None) -> Dict[str, Any]:
    ticker = ticker.upper()
    logger.info(f"--- [LANGGRAPH] Starting pipeline for {ticker} ---")

    initial_state: StockState = {
        "ticker":        ticker,
        "research_data": None,
        "analysis_data": None,
        "recommendation": None,
        "error":         None,
        "progress_cb":   progress_cb,
    }

    # ── Gọi LangGraph compiled graph — runtime quản lý state + conditional edges
    final_state = await _graph.ainvoke(initial_state)

    if final_state.get("error"):
        return {"ticker": ticker, "status": "error", "error": final_state["error"]}

    recommendation = final_state.get("recommendation")
    analysis       = final_state.get("analysis_data")

    if not recommendation or not analysis:
        logger.error(f"[LANGGRAPH] Pipeline incomplete for {ticker}: recommendation={'set' if recommendation else 'None'}, analysis={'set' if analysis else 'None'}")
        return {"ticker": ticker, "status": "error", "error": "Pipeline did not complete successfully"}

    # Gắn metadata, price_history và agent_trace
    recommendation["fallback_used"] = analysis.get("fallback_used", False)
    recommendation["data_points"]   = analysis.get("data_points", 0)

    # Pass price history (oldest→newest) for frontend chart
    research    = final_state.get("research_data", {})
    raw_prices  = research.get("prices", [])
    recommendation["price_history"] = list(reversed(raw_prices))
    rsi_val  = analysis.get("rsi")
    macd_val = analysis.get("macd_histogram")
    atr_val  = analysis.get("atr")
    score    = recommendation.get("score", 0)

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
