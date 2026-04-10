import os
import fitz  # PyMuPDF
import tempfile
import aiohttp
from typing import List, Dict, Any
from langchain_text_splitters import RecursiveCharacterTextSplitter
import logging

logger = logging.getLogger(__name__)

class PDFProcessorService:
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ".", " ", ""]
        )

    async def download_pdf(self, url: str) -> str:
        """Downloads a PDF from a URL to a temporary file."""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        raise Exception(f"Failed to download PDF: {response.status}")
                    
                    # Create temporary file
                    fd, path = tempfile.mkstemp(suffix=".pdf")
                    with os.fdopen(fd, 'wb') as f:
                        f.write(await response.read())
                    return path
        except Exception as e:
            logger.error(f"Error downloading PDF from {url}: {e}")
            raise e

    def extract_text_from_pdf(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Extracts text from a local PDF file page by page.
        Returns a list of dicts: {"text": "...", "page_number": int}
        """
        pages_content = []
        try:
            doc = fitz.open(file_path)
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                text = page.get_text()
                # Clean up text by removing consecutive newlines or excessive spaces if needed
                text = " ".join(text.split())
                if text.strip():
                    pages_content.append({
                        "text": text,
                        "page_number": page_num + 1
                    })
            doc.close()
            return pages_content
        except Exception as e:
            logger.error(f"Error reading PDF {file_path}: {e}")
            raise e

    def process_and_chunk_pdf(
        self,
        file_path: str,
        base_metadata: Dict[str, Any],
        document_id: str = "",
    ) -> List[Dict[str, Any]]:
        """
        Extracts text, chunks it, and attaches metadata.
        base_metadata should contain: ticker, doc_type, period, year, source.
        document_id is used to generate chunk_id for MongoDB<->Pinecone linking.
        """
        pages = self.extract_text_from_pdf(file_path)
        chunks_with_metadata = []
        global_chunk_index = 0

        for page in pages:
            text = page["text"]
            chunks = self.text_splitter.split_text(text)

            for chunk in chunks:
                chunk_metadata = base_metadata.copy()
                chunk_metadata["page"] = page["page_number"]
                chunk_metadata["chunk_index"] = global_chunk_index
                chunk_metadata["document_id"] = document_id
                chunk_metadata["chunk_id"] = f"{document_id}_chunk_{global_chunk_index:04d}"
                chunk_metadata["source_file"] = base_metadata.get("source", "")
                chunk_metadata["text"] = chunk

                chunks_with_metadata.append({
                    "text": chunk,
                    "metadata": chunk_metadata,
                })
                global_chunk_index += 1

        return chunks_with_metadata

    async def auto_download_and_process(self, url: str, base_metadata: Dict[str, Any], document_id: str = "") -> List[Dict[str, Any]]:
        """Convenience method: Download, process, chunk, and clean up."""
        file_path = ""
        try:
            file_path = await self.download_pdf(url)
            chunks = self.process_and_chunk_pdf(file_path, base_metadata, document_id=document_id)
            return chunks
        finally:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
