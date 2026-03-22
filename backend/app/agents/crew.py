import asyncio
from typing import Dict, Any
from app.agents.market_researcher import research_stock
from app.agents.financial_analyst import analyze_financials
from app.agents.investment_advisor import get_recommendation

async def run_analysis(ticker: str) -> Dict[str, Any]:
    """
    Rule-based analysis orchestrator.
    Replaces CrewAI sequential process with simple async calls.
    """
    print(f"[*] Starting rule-based analysis for {ticker}")
    
    # 1. Market Research (Async)
    research_data = await research_stock(ticker)
    research_data["symbol"] = ticker
    
    if "error" in research_data.get("prices", {}):
        return {
            "symbol": ticker,
            "price": 0,
            "trend": "error",
            "recommendation": "ERROR",
            "confidence": 0,
            "error": research_data["prices"]["message"]
        }

    # 2. Financial Analysis (Sync logic)
    analysis = analyze_financials(research_data)
    analysis["symbol"] = ticker
    
    # 3. Investment Recommendation (Sync logic)
    recommendation = get_recommendation(analysis)
    
    # Add risk/opportunity field to match frontend expected schema if needed
    # (Based on the old FinalReport model)
    recommendation["risk_opportunity"] = f"MA5: {analysis.get('ma5',0):.2f}, MA20: {analysis.get('ma20',0):.2f}. Volume Change: {analysis.get('volume_change',0)*100:.1f}%."
    
    return recommendation
