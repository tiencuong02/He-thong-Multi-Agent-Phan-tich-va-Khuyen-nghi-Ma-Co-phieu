import asyncio
import os
from dotenv import load_dotenv
from app.agents.crew import run_analysis
from app.db.mongodb import connect_to_mongo

load_dotenv()

async def debug():
    await connect_to_mongo()
    ticker = "GOOGL"
    print(f"Running analysis for {ticker}...")
    try:
        result = await run_analysis(ticker)
        print("Result:")
        print(result)
    except Exception as e:
        print(f"FAILED with exception: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(debug())
