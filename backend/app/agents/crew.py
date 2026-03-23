import asyncio
import logging
from typing import Dict, Any

from app.agents.market_researcher import research_stock
from app.agents.financial_analyst import analyze_financials
from app.agents.investment_advisor import get_recommendation

logger = logging.getLogger(__name__)

class StockAnalysisOrchestrator:
    """
    Manages the multi-agent execution pipeline.
    Ensures data consistency and provides a clear trace of agent actions.
    """
    
    @staticmethod
    async def run_full_analysis(ticker: str) -> Dict[str, Any]:
        ticker = ticker.upper()
        logger.info(f"--- [ORCHESTRATOR] Starting Analysis for {ticker} ---")
        
        # 1. Market Research (Data Gathering)
        # ----------------------------------
        logger.info(f"[ORCHESTRATOR] Step 1: Triggering Market Researcher")
        research_data = await research_stock(ticker)
        
        if "error" in research_data:
            logger.error(f"[ORCHESTRATOR] Research failed for {ticker}: {research_data.get('error')}")
            return {
                "ticker": ticker,
                "status": "error",
                "error": research_data.get("error")
            }

        # 2. Financial Analysis (Metrics Computing)
        # ----------------------------------------
        logger.info(f"[ORCHESTRATOR] Step 2: Triggering Financial Analyst")
        # In a real agentic flow, we'd pass JSON/Markdown to an LLM. 
        # Here we pass the data dict to our rule-based analyst.
        analysis_res = analyze_financials(research_data)
        
        if "error" in analysis_res:
            logger.error(f"[ORCHESTRATOR] Analysis failed for {ticker}")
            return {**analysis_res, "status": "error"}

        # 3. Investment Recommendation (Decision Making)
        # ---------------------------------------------
        logger.info(f"[ORCHESTRATOR] Step 3: Triggering Investment Advisor")
        recommendation = get_recommendation(analysis_res)
        
        # Add metadata for the UI to show the "Agent Trace"
        recommendation["agent_trace"] = [
            {"agent": "Market Researcher", "status": "completed", "tools": ["AlphaVantage", "Playwright"]},
            {"agent": "Financial Analyst", "status": "completed", "logic": "Rule-Based"},
            {"agent": "Investment Advisor", "status": "completed", "logic": "Rule-Based"}
        ]
        
        logger.info(f"--- [ORCHESTRATOR] Analysis Completed for {ticker} ---")
        return recommendation

async def run_analysis(ticker: str) -> Dict[str, Any]:
    """Compatibility wrapper for the worker"""
    return await StockAnalysisOrchestrator.run_full_analysis(ticker)
