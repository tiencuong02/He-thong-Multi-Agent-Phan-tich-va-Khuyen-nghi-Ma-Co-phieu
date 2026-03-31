import asyncio
import os
import sys
import logging

# Set up logging to console
logging.basicConfig(level=logging.INFO)

# Force project root into path
sys.path.append(os.getcwd())

from app.services.rag.vector_store import VectorStoreService
from app.services.rag.rag_pipeline import RAGPipelineService

async def main():
    print("--- [RAG Query Test] ---")
    
    # 1. Initialize Vector Store
    print("Step 1: Initializing Vector Store...")
    vs = VectorStoreService()
    
    # 2. Initialize RAG Pipeline
    print("Step 2: Initializing RAG Pipeline...")
    rag = RAGPipelineService(vs)
    
    if not rag.llm:
        print("❌ Error: LLM not initialized. Check GEMINI_API_KEY.")
        return

    # 3. Perform Query
    query = "Cho tôi biết tổng tài sản của FPTS trong báo cáo gần nhất là bao nhiêu?"
    print(f"Step 3: Querying: '{query}'")
    
    try:
        result = await rag.answer_query(query)
        print("\n--- [RESULT] ---")
        print(f"Answer: {result.get('answer')[:200]}...")
        print(f"Ticker: {result.get('ticker_identified')}")
        print(f"Sources count: {len(result.get('sources', []))}")
    except Exception as e:
        print(f"❌ Error during query: {e}")

if __name__ == "__main__":
    asyncio.run(main())
