from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional, List
from app.models.user import User
from app.api.endpoints.auth import get_current_user, check_admin_role
from app.services.rag.vector_store import VectorStoreService
from app.services.rag.rag_pipeline import RAGPipelineService
from app.services.rag.pdf_processor import PDFProcessorService
from app.db.mongodb import get_db
from bson import ObjectId
import tempfile
import os
import datetime
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# Dependency to get RAG service
def get_rag_service():
    vector_store = VectorStoreService()
    return RAGPipelineService(vector_store)

class RAGQuery(BaseModel):
    query: str

# ─── Query Endpoint ───────────────────────────────────────────────────────────
@router.post("/query/")
async def process_rag_query(
    request: RAGQuery,
    service: RAGPipelineService = Depends(get_rag_service),
    current_user: User = Depends(get_current_user)
):
    try:
        response = await service.answer_query(request.query)
        return response
    except Exception as e:
        logger.error(f"RAG query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ─── Upload PDF Endpoint (Admin Only) ─────────────────────────────────────────
@router.post("/upload/")
async def upload_pdf(
    file: UploadFile = File(...),
    ticker: str = Form(...),
    doc_type: str = Form("Báo cáo tài chính"),
    period: str = Form(""),
    year: str = Form("2024"),
    current_user: User = Depends(check_admin_role),
    db=Depends(get_db)
):
    """Admin endpoint: upload a PDF file, process it, and store embeddings in Pinecone."""
    
    # Validate file type
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Chỉ chấp nhận file PDF.")
    
    # Save uploaded file to a temp location
    tmp_path = ""
    try:
        content = await file.read()
        fd, tmp_path = tempfile.mkstemp(suffix=".pdf")
        with os.fdopen(fd, "wb") as f:
            f.write(content)
        
        # Process PDF: extract text, chunk, create embeddings
        processor = PDFProcessorService()
        metadata = {
            "ticker": ticker.upper().strip(),
            "doc_type": doc_type,
            "period": period,
            "year": year,
            "source": file.filename
        }
        
        chunks = processor.process_and_chunk_pdf(tmp_path, metadata)
        
        if not chunks:
            raise HTTPException(status_code=400, detail="Không trích xuất được nội dung từ file PDF.")
        
        # Upsert chunks to Pinecone
        vector_store = VectorStoreService()
        success = vector_store.upsert_chunks(chunks)
        
        if not success:
            raise HTTPException(status_code=500, detail="Lỗi khi lưu vào vector store. Kiểm tra Pinecone API key.")
        
        # Save document record to MongoDB
        doc_record = {
            "filename": file.filename,
            "ticker": ticker.upper().strip(),
            "doc_type": doc_type,
            "period": period,
            "year": year,
            "chunks_count": len(chunks),
            "uploaded_by": current_user.username,
            "uploaded_at": datetime.datetime.utcnow().isoformat(),
        }
        
        if db is not None:
            result = await db["knowledge_base"].insert_one(doc_record)
            doc_record["_id"] = str(result.inserted_id)
        
        logger.info(f"PDF uploaded: {file.filename} | Ticker: {ticker} | Chunks: {len(chunks)}")
        
        return {
            "status": "success",
            "message": f"Đã xử lý thành công {file.filename}",
            "chunks_processed": len(chunks),
            "document": {
                "id": doc_record.get("_id", ""),
                "filename": file.filename,
                "ticker": ticker.upper().strip(),
                "doc_type": doc_type,
                "period": period,
                "year": year,
                "chunks_count": len(chunks),
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Lỗi xử lý file: {str(e)}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)

# ─── List Documents Endpoint (Admin Only) ─────────────────────────────────────
@router.get("/documents/")
async def list_documents(
    current_user: User = Depends(check_admin_role),
    db=Depends(get_db)
):
    """Get all ingested documents from knowledge base."""
    if db is None:
        return []
    
    try:
        cursor = db["knowledge_base"].find().sort("uploaded_at", -1)
        documents = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            documents.append(doc)
        return documents
    except Exception as e:
        logger.error(f"Failed to list documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ─── Delete Document Endpoint (Admin Only) ────────────────────────────────────
@router.delete("/documents/{doc_id}/")
async def delete_document(
    doc_id: str,
    current_user: User = Depends(check_admin_role),
    db=Depends(get_db)
):
    """Delete a document record from the knowledge base."""
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")
    
    try:
        result = await db["knowledge_base"].delete_one({"_id": ObjectId(doc_id)})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Document not found")
        
        logger.info(f"Document {doc_id} deleted by {current_user.username}")
        return {"status": "success", "message": "Đã xóa tài liệu"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete document: {e}")
        raise HTTPException(status_code=500, detail=str(e))
