import os
import sys
import asyncio
from dotenv import load_dotenv

# Add current directory to path
sys.path.append(os.getcwd())
load_dotenv(".env")

from app.services.rag.pdf_processor import PDFProcessorService
from app.services.rag.vector_store import VectorStoreService

async def ingest_file(url, ticker, title, doc_type="Annual Report"):
    print(f"🚀 Processing {ticker} from {url}...")
    
    processor = PDFProcessorService()
    vector_store = VectorStoreService()
    
    if not vector_store.vector_store:
        print("❌ Vector Store not ready.")
        return

    metadata = {
        "ticker": ticker,
        "source": "Investor Relations",
        "doc_type": doc_type,
        "period": title,
        "original_url": url
    }
    
    try:
        chunks = await processor.auto_download_and_process(url, metadata)
        if chunks:
            print(f"✅ Extracted {len(chunks)} chunks. Upserting...")
            success = vector_store.upsert_chunks(chunks)
            if success:
                print(f"✨ Successfully ingested {ticker} - {title}")
            else:
                print(f"❌ Failed to upsert {ticker}")
        else:
            print(f"⚠️ No text extracted for {ticker}")
    except Exception as e:
        print(f"❌ Error: {e}")

async def main():
    # Alphabet Q4 2023 (Google) - using a direct link from abc.xyz
    await ingest_file(
        "https://www.abc.xyz/assets/investor/static/pdf/20231231_alphabet_10K.pdf",
        "GOOGL",
        "Annual Report 2023"
    )
    
    # Tesla Q4 2023 
    # (Already ingested in last run, but safe to repeat or we could skip)
    print("Tesla already ingested. Skipping to save time.")

if __name__ == "__main__":
    asyncio.run(main())
