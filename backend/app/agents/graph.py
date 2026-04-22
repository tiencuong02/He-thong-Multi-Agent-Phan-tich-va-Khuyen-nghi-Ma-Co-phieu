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


async def advisor_node(state: StockState) -> StockState:
    logger.info(f"[LANGGRAPH] Node 3: Investment Advisor — {state['ticker']}")
    result = await get_recommendation(state["analysis_data"])
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
# Public entry point (giữ nguyên interface cũ)
# ---------------------------------------------------------------------------
async def run_analysis(ticker: str) -> Dict[str, Any]:
    ticker = ticker.upper()
    logger.info(f"--- [LANGGRAPH] Starting pipeline for {ticker} ---")

    initial_state: StockState = {
        "ticker": ticker,
        "research_data": None,
        "analysis_data": None,
        "recommendation": None,
        "error": None,
    }

    try:
        final_state = await _graph.ainvoke(initial_state)
    except Exception as e:
        logger.error(f"[LANGGRAPH] Pipeline exception for {ticker}: {e}")
        return {"ticker": ticker, "status": "error", "error": str(e)}

    if not final_state or final_state.get("error"):
        error_msg = final_state.get("error") if final_state else "Pipeline returned no state"
        return {"ticker": ticker, "status": "error", "error": error_msg}

    recommendation = final_state.get("recommendation")
    analysis = final_state.get("analysis_data")

    if not recommendation or not analysis:
        logger.error(f"[LANGGRAPH] Pipeline incomplete for {ticker}: recommendation={'set' if recommendation else 'None'}, analysis={'set' if analysis else 'None'}")
        return {"ticker": ticker, "status": "error", "error": "Pipeline did not complete successfully"}

    # Gắn metadata, price_history và agent_trace
    recommendation["fallback_used"] = analysis.get("fallback_used", False)
    recommendation["data_points"]   = analysis.get("data_points", 0)

    # Pass price history (oldest→newest) for frontend chart
    raw_prices = final_state.get("research_data", {}).get("prices", [])
    recommendation["price_history"] = list(reversed(raw_prices))
    recommendation["agent_trace"]   = [
        {
            "agent": "Market Researcher",
            "status": "completed",
            "tools": ["yfinance", "AlphaVantage"],
            "data": f"Fetched {analysis.get('data_points', 0)} days, {analysis.get('news_count', 0)} news"
        },
        {
            "agent": "Financial Analyst",
            "status": "completed",
            "logic": "Rule-Based + Sentiment",
            "fallback": analysis.get("fallback_used", False),
            "sentiment": analysis.get("sentiment_label", "Trung lập")
        },
        {
            "agent": "Investment Advisor",
            "status": "completed",
            "logic": "Rule-Based + Gemini LLM",
            "overall_assessment": recommendation.get("overall_assessment", "Trung lập")
        }
    ]

    logger.info(f"--- [LANGGRAPH] Pipeline completed for {ticker} ---")
    return recommendation
