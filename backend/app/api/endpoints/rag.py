from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from app.models.user import User
from app.api.endpoints.auth import get_current_user, check_admin_role
from app.services.rag.vector_store import VectorStoreService
from app.services.rag.rag_pipeline import RAGPipelineService
from app.services.rag.pdf_processor import PDFProcessorService
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# Dependency to get RAG service
def get_rag_service():
    vector_store = VectorStoreService()
    return RAGPipelineService(vector_store)

class RAGQuery(BaseModel):
    query: str

class IngestRequest(BaseModel):
    url: str
    ticker: str
    doc_type: str = "Báo cáo tài chính"
    period: str = "2024"
    source: str = "Tên Công Ty"

@router.post("/query")
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

@router.post("/ingest")
async def ingest_pdf_url(
    request: IngestRequest,
    current_user: User = Depends(check_admin_role)
):
    """Admin only endpoint to ingest a new PDF from a URL into the knowledge base"""
    try:
        processor = PDFProcessorService()
        vector_store = VectorStoreService()
        
        metadata = {
            "ticker": request.ticker.upper(),
            "doc_type": request.doc_type,
            "period": request.period,
            "source": request.source
        }
        
        chunks = await processor.auto_download_and_process(request.url, metadata)
        
        success = vector_store.upsert_chunks(chunks)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to upsert to vector store")
            
        return {"status": "success", "chunks_processed": len(chunks)}
    except Exception as e:
        logger.error(f"Ingest failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
