import asyncio
import sys
import os

# Add the project root to sys.path to handle imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.agents.tools.browser_tool import BrowserTool

async def test():
    print("Testing BrowserTool...")
    results = await BrowserTool.fetch_news_from_web("VNM")
    print(f"Found {len(results)} news items.")
    for r in results:
        print(f"- {r['title']} ({r['source']})")

if __name__ == "__main__":
    asyncio.run(test())
