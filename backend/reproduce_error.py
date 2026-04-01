import asyncio
import logging
import sys
import os

# Ensure the app could be imported
sys.path.append(os.getcwd())

from app.agents.crew import run_analysis

async def test():
    logging.basicConfig(level=logging.INFO)
    ticker = "META"
    print(f"--- Testing Analysis for {ticker} ---")
    try:
        result = await run_analysis(ticker)
        print("\nRESULT KEYS:", list(result.keys()))
        for k, v in result.items():
            if isinstance(v, str):
                # Safe print for Windows console: ignore non-ASCII
                safe_val = v.encode('ascii', 'ignore').decode('ascii')
                print(f"  {k}: {safe_val[:100]}...")
            else:
                print(f"  {k}: {v}")
                
        # Check if it satisfies AnalysisResult
        from app.models.stock import AnalysisResult
        # Handle the symbol -> ticker rename if it wasn't done
        if "symbol" in result and "ticker" not in result:
            result["ticker"] = result.pop("symbol")
            
        obj = AnalysisResult(**result)
        print("\nSUCCESS: AnalysisResult validation passed.")
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Fix for Windows Proactor loop issue
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(test())
