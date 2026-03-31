import os
import sys
from dotenv import load_dotenv

# Add the current directory to sys.path to allow imports
sys.path.append(os.getcwd())

# Force load .env
load_dotenv(".env")

from app.services.rag.vector_store import VectorStoreService
from app.services.rag.rag_pipeline import RAGPipelineService

def test_rag_status():
    print("--- [RAG DIAGNOSTIC] ---")
    
    # 1. Check API Keys
    openai_key = os.getenv("OPENAI_API_KEY")
    pinecone_key = os.getenv("PINECONE_API_KEY")
    index_name = os.getenv("PINECONE_INDEX_NAME", "stock-reports-free")
    
    print(f"OpenAI Key: {'[SET]' if openai_key else '[MISSING]'}")
    print(f"Pinecone Key: {'[SET]' if pinecone_key else '[MISSING]'}")
    print(f"Pinecone Index: {index_name}")
    
    if not all([openai_key, pinecone_key, index_name]):
        print("\n❌ Error: Missing configuration in .env")
        return

    # 2. Test Vector Store Initialization
    print("\n[STEP 1] Testing VectorStoreService initialization...")
    try:
        vs = VectorStoreService()
        if vs.vector_store:
            print("✅ VectorStoreService initialized and connected to Pinecone successfully.")
        else:
            print("❌ VectorStoreService failed to connect to Pinecone.")
            print(f"👉 Please ensure you have created an index named '{index_name}' in your Pinecone dashboard.")
            print(f"👉 Configuration: Dimension=384, Metric=cosine, Cloud=aws, Region=us-east-1.")
            return
    except Exception as e:
        print(f"❌ Critical Error initializing VectorStoreService: {e}")
        return

    # 3. Test RAG Pipeline Initialization
    print("\n[STEP 2] Testing RAGPipelineService initialization...")
    try:
        pipeline = RAGPipelineService(vs)
        if pipeline.llm:
            print("✅ RAGPipelineService and ChatOpenAI initialized successfully.")
        else:
            print("❌ RAGPipelineService failed to initialize LLM (Check OpenAI key).")
            return
    except Exception as e:
        print(f"❌ Critical Error initializing RAGPipelineService: {e}")
        return

    # 4. Deep Test: Embedding Call
    print("\n[STEP 3] Testing Local Embedding (HuggingFace)...")
    try:
        test_text = "Thử nghiệm kết nối"
        res = vs.embeddings.embed_query(test_text)
        if res and len(res) == 384:
            print(f"✅ Local Embedding successful! Dimension: {len(res)} (Correct for MiniLM-L12).")
        else:
            print(f"❌ Embedding test failed or returned wrong dimension: {len(res) if res else 'None'}")
    except Exception as e:
        print(f"❌ Error during local embedding test: {e}")
        return

    # 5. Final Status
    print("\n🎉 Overall RAG Status: ACTIVE & READY")
    print("Reminder: Use the /api/v1/rag/ingest endpoint to add PDFs before querying.")

if __name__ == "__main__":
    test_rag_status()
