import os
import re
import fitz  # PyMuPDF
import tempfile
import aiohttp
from typing import List, Dict, Any, Tuple
from langchain_text_splitters import RecursiveCharacterTextSplitter
import logging

logger = logging.getLogger(__name__)

# Hierarchical chunk sizes — Small-to-Big Retrieval pattern
# Child chunk: nhỏ, dùng để retrieve chính xác
# Parent chunk: lớn, đưa vào LLM để có đủ context
# Tăng size để giảm tổng chunk → giảm thời gian embedding trên CPU
CHILD_CHUNK_SIZE    = 1500  # Tăng lên 1500 để giảm số lượng chunk (tăng tốc CPU embed)
CHILD_CHUNK_OVERLAP = 200
PARENT_CHUNK_SIZE   = 3000  # Tăng lên 3000 để bao trọn child chunk lớn hơn
PARENT_CHUNK_OVERLAP = 300



class PDFProcessorService:
    def __init__(
        self,
        child_chunk_size: int = CHILD_CHUNK_SIZE,
        child_chunk_overlap: int = CHILD_CHUNK_OVERLAP,
        parent_chunk_size: int = PARENT_CHUNK_SIZE,
        parent_chunk_overlap: int = PARENT_CHUNK_OVERLAP,
    ):
        # Child splitter — dùng để embed và retrieve
        self._child_splitter = RecursiveCharacterTextSplitter(
            chunk_size=child_chunk_size,
            chunk_overlap=child_chunk_overlap,
            separators=["\n\n", "\n", ".", "，", " ", ""],
            keep_separator=True,
        )
        # Parent splitter — dùng để build context đưa vào LLM
        self._parent_splitter = RecursiveCharacterTextSplitter(
            chunk_size=parent_chunk_size,
            chunk_overlap=parent_chunk_overlap,
            separators=["\n\n\n", "\n\n", "\n", ".", " ", ""],
            keep_separator=True,
        )

    # ─── Download ─────────────────────────────────────────────────────────────

    async def download_pdf(self, url: str) -> str:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    raise Exception(f"PDF download failed: HTTP {resp.status}")
                fd, path = tempfile.mkstemp(suffix=".pdf")
                with os.fdopen(fd, "wb") as f:
                    f.write(await resp.read())
                return path

    # ─── PDF Text Extraction — giữ nguyên cấu trúc ───────────────────────────

    def extract_pages(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Trích xuất text từ PDF theo từng trang, giữ nguyên cấu trúc:
        - Text thường: giữ newline để bảo toàn đoạn văn
        - Bảng biểu: nhận dạng và format dạng text có cấu trúc
        - Số liệu tài chính: KHÔNG join thành 1 dòng (khác với code cũ)
        """
        pages = []
        try:
            doc = fitz.open(file_path)
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                page_text = self._extract_page_content(page)
                if page_text.strip():
                    pages.append({
                        "text": page_text,
                        "page_number": page_num + 1,
                    })
            doc.close()
        except Exception as e:
            logger.error(f"PDF extraction failed: {e}")
            raise
        return pages

    def _extract_page_content(self, page) -> str:
        """
        Dùng fitz blocks để phân biệt text block vs table.
        Giữ newline — KHÔNG dùng ' '.join(text.split()) nữa.
        """
        blocks = page.get_text("blocks", sort=True)
        parts = []
        for block in blocks:
            # block = (x0, y0, x1, y1, text, block_no, block_type)
            # block_type: 0 = text, 1 = image
            if block[6] != 0:
                continue  # bỏ qua image blocks
            raw = block[4]
            cleaned = self._clean_text_block(raw)
            if cleaned:
                parts.append(cleaned)

        return "\n\n".join(parts)

    @staticmethod
    def _clean_text_block(text: str) -> str:
        """
        Làm sạch nhẹ — chỉ loại bỏ ký tự thừa, KHÔNG phá vỡ cấu trúc.
        """
        # Chuẩn hoá khoảng trắng trong dòng nhưng giữ nguyên newline
        lines = text.split("\n")
        cleaned_lines = []
        for line in lines:
            line = re.sub(r"[ \t]+", " ", line).strip()
            if line:
                cleaned_lines.append(line)
        return "\n".join(cleaned_lines)

    # ─── Hierarchical Chunking (Small-to-Big) ────────────────────────────────

    def process_and_chunk_pdf(
        self,
        file_path: str,
        base_metadata: Dict[str, Any],
        document_id: str = "",
    ) -> List[Dict[str, Any]]:
        """
        Hierarchical chunking:
        1. Split thành parent chunks (context lớn cho LLM)
        2. Mỗi parent split tiếp thành child chunks (nhỏ cho retrieval)
        3. Child chunk embed + lưu vào vector store, nhưng metadata chứa parent_text
           để khi retrieve child, LLM nhận được parent context đầy đủ.

        Trả về list chunk để upsert — mỗi item là child chunk nhưng
        page_content (text embed) là child, metadata["parent_text"] là parent.
        """
        pages = self.extract_pages(file_path)
        all_chunks: List[Dict[str, Any]] = []
        global_idx = 0

        for page in pages:
            page_text = page["text"]
            page_num = page["page_number"]

            # Tạo parent chunks từ page text
            parent_chunks = self._parent_splitter.split_text(page_text)

            for p_idx, parent_text in enumerate(parent_chunks):
                if not parent_text.strip():
                    continue

                # Tạo child chunks từ parent
                child_chunks = self._child_splitter.split_text(parent_text)

                for c_idx, child_text in enumerate(child_chunks):
                    child_text = child_text.strip()
                    if len(child_text) < 20:
                        continue  # bỏ chunk quá ngắn

                    chunk_meta = base_metadata.copy()
                    chunk_meta.update({
                        "page":          page_num,
                        "parent_index":  p_idx,
                        "chunk_index":   global_idx,
                        "document_id":   document_id,
                        "chunk_id":      f"{document_id}_p{p_idx:03d}_c{c_idx:03d}_{global_idx:04d}",
                        "source_file":   base_metadata.get("source", ""),
                        # parent_text lưu vào metadata — khi retrieve child,
                        # pipeline dùng parent_text thay vì child_text để đưa vào LLM
                        "parent_text":   parent_text[:2000],  # cap để tránh metadata quá lớn
                        "has_table":     self._has_table_pattern(child_text),
                        "has_numbers":   self._has_financial_numbers(child_text),
                    })

                    all_chunks.append({
                        "text":     child_text,   # text embed vào vector store
                        "metadata": chunk_meta,
                    })
                    global_idx += 1

        logger.info(
            f"PDF processed: {len(pages)} pages → {global_idx} child chunks. "
            f"File: {base_metadata.get('source', file_path)}"
        )
        return all_chunks

    # ─── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _has_table_pattern(text: str) -> bool:
        """Phát hiện block có thể là bảng (nhiều số, dấu phân cách)."""
        # Bảng tài chính thường có nhiều số và các ký tự phân tách
        number_count = len(re.findall(r"\d[\d,.]+", text))
        return number_count >= 4

    @staticmethod
    def _has_financial_numbers(text: str) -> bool:
        """Phát hiện số liệu tài chính (tỷ, triệu, %, VND)."""
        patterns = [r"\d+[.,]\d+", r"tỷ|triệu|nghìn", r"%", r"VND|đồng|VNĐ"]
        return any(re.search(p, text, re.IGNORECASE) for p in patterns)

    async def auto_download_and_process(
        self,
        url: str,
        base_metadata: Dict[str, Any],
        document_id: str = "",
    ) -> List[Dict[str, Any]]:
        """Download PDF từ URL, process, chunk, cleanup."""
        file_path = ""
        try:
            file_path = await self.download_pdf(url)
            return self.process_and_chunk_pdf(file_path, base_metadata, document_id=document_id)
        finally:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
