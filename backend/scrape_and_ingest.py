import os
import sys
import asyncio
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from urllib.parse import urljoin

# Add current directory to path
sys.path.append(os.getcwd())
load_dotenv(".env")

from app.services.rag.pdf_processor import PDFProcessorService
from app.services.rag.vector_store import VectorStoreService

async def scrape_and_ingest(url, ticker):
    print(f"🚀 Starting scraper for {ticker} at {url}...")
    
    # 1. Fetch the page
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print(f"❌ Failed to fetch page: {e}")
        return

    soup = BeautifulSoup(response.text, 'html.parser')
    
    # 2. Find all PDF links
    pdf_links = []
    for a in soup.find_all('a', href=True):
        href = a['href']
        if href.lower().endswith('.pdf'):
            full_url = urljoin(url, href)
            title = a.get_text(strip=True)
            if not title:
                title = href.split('/')[-1]
            pdf_links.append({"url": full_url, "title": title})

    if not pdf_links:
        print("⚠️ No PDF links found on this page.")
        return

    print(f"🔍 Found {len(pdf_links)} PDF documents. Starting ingestion...")

    # 3. Initialize Services
    processor = PDFProcessorService()
    vector_store = VectorStoreService()
    
    if not vector_store.vector_store:
        print("❌ Vector Store not ready. Check your .env/Pinecone status.")
        return

    # 4. Process each PDF (limiting to top 5 for initial test to avoid timeout/overload)
    # You can remove the [:5] to process everything.
    for doc in pdf_links[:5]:
        print(f"\n📄 Processing: {doc['title']}")
        print(f"🔗 URL: {doc['url']}")
        
        try:
            # Metadata extraction from title (simple heuristic)
            metadata = {
                "ticker": ticker,
                "source": "FPTS IR",
                "doc_type": "Báo cáo tài chính",
                "period": doc['title'], # Use title as period for now
                "original_url": doc['url']
            }
            
            # Download and chunk
            chunks = await processor.auto_download_and_process(doc['url'], metadata)
            
            if chunks:
                print(f"✅ Extracted {len(chunks)} chunks. Upserting to Pinecone...")
                success = vector_store.upsert_chunks(chunks)
                if success:
                    print(f"✨ Successfully ingested {doc['title']}")
                else:
                    print(f"❌ Failed to upsert {doc['title']}")
            else:
                print(f"⚠️ No text extracted from {doc['title']}")
                
        except Exception as e:
            print(f"❌ Error processing {doc['title']}: {e}")

    print("\n✅ Ingestion process completed!")

if __name__ == "__main__":
    TARGET_URL = "https://fpts.com.vn/quan-he-co-dong/thong-tin-tai-chinh/"
    TICKER = "FTS" # FPTS ticker is FTS
    
    asyncio.run(scrape_and_ingest(TARGET_URL, TICKER))
