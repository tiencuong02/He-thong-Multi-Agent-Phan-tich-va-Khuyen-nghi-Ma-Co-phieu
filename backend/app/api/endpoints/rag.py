from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from pydantic import BaseModel, Field
from typing import Optional, List
from app.models.user import User
from app.api.endpoints.auth import get_current_user, check_admin_role
from app.services.rag.vector_store import VectorStoreService
from app.services.rag.rag_pipeline import RAGPipelineService
from app.services.rag.pdf_processor import PDFProcessorService
from app.db.mongodb import get_db
from app.core.config import settings
from bson import ObjectId
import tempfile
import os
import datetime
import logging
import uuid

logger = logging.getLogger(__name__)
router = APIRouter()

# Singleton dependencies from app.state (initialized once at startup)
def get_rag_service(request: Request) -> RAGPipelineService:
    service = getattr(request.app.state, "rag_pipeline", None)
    if service is None:
        raise HTTPException(status_code=503, detail="RAG service chưa sẵn sàng. Vui lòng thử lại sau.")
    return service

def get_vector_store(request: Request) -> VectorStoreService:
    store = getattr(request.app.state, "vector_store", None)
    if store is None:
        raise HTTPException(status_code=503, detail="Vector store chưa sẵn sàng. Vui lòng thử lại sau.")
    return store

class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., max_length=2000)

class RAGQuery(BaseModel):
    query: str = Field(..., min_length=1, max_length=500, description="Câu hỏi (tối đa 500 ký tự)")
    conversation_history: Optional[List[ChatMessage]] = Field(default=None, max_length=10, description="Lịch sử hội thoại (tối đa 10 messages)")

class CompareQuery(BaseModel):
    query: str = Field(..., min_length=1, max_length=500, description="Câu hỏi so sánh (tối đa 500 ký tự)")
    tickers: Optional[List[str]] = Field(default=None, max_length=3, description="Danh sách mã cổ phiếu để so sánh (tối đa 3)")
    conversation_history: Optional[List[ChatMessage]] = Field(default=None, max_length=10, description="Lịch sử hội thoại (tối đa 10 messages)")

# ─── Query Endpoint ───────────────────────────────────────────────────────────
@router.post("/query/")
async def process_rag_query(
    request: RAGQuery,
    service: RAGPipelineService = Depends(get_rag_service),
    current_user: User = Depends(get_current_user)
):
    try:
        history = None
        if request.conversation_history:
            history = [{"role": m.role, "content": m.content} for m in request.conversation_history]
        response = await service.answer_query(request.query, conversation_history=history)
        return response
    except Exception as e:
        logger.error(f"RAG query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ─── Streaming Query Endpoint (SSE) ──────────────────────────────────────────
from fastapi.responses import StreamingResponse
import json

@router.post("/query/stream")
async def process_rag_query_stream(
    request: RAGQuery,
    service: RAGPipelineService = Depends(get_rag_service),
    current_user: User = Depends(get_current_user)
):
    history = None
    if request.conversation_history:
        history = [{"role": m.role, "content": m.content} for m in request.conversation_history]

    async def event_generator():
        try:
            async for chunk in service.answer_query_stream(request.query, conversation_history=history):
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.error(f"RAG stream failed: {e}")
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

# ─── Comparison Query Endpoint (SSE) ──────────────────────────────────────
@router.post("/query/compare/stream")
async def compare_tickers_stream(
    request: CompareQuery,
    service: RAGPipelineService = Depends(get_rag_service),
    current_user: User = Depends(get_current_user)
):
    """
    Streaming comparison endpoint: compare 2-3 tickers side-by-side.
    Tickers can be provided explicitly or extracted from query.
    """
    history = None
    if request.conversation_history:
        history = [{"role": m.role, "content": m.content} for m in request.conversation_history]

    # Extract tickers: use provided tickers or parse from query
    tickers = request.tickers or service._extract_tickers_multi(request.query)

    if len(tickers) < 2:
        async def err_gen():
            yield f"data: {json.dumps({'type': 'error', 'content': 'Cần ít nhất 2 mã cổ phiếu để so sánh.'}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(err_gen(), media_type="text/event-stream")

    async def event_generator():
        try:
            async for chunk in service.compare_tickers_stream(request.query, tickers, conversation_history=history):
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.error(f"RAG compare stream failed: {e}")
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

# ─── Upload PDF Endpoint (Admin Only) ─────────────────────────────────────
@router.post("/upload/")
async def upload_pdf(
    file: UploadFile = File(...),
    ticker: str = Form(...),
    doc_type: str = Form("Báo cáo tài chính"),
    period: str = Form(""),
    year: str = Form("2024"),
    current_user: User = Depends(check_admin_role),
    vector_store: VectorStoreService = Depends(get_vector_store),
    db=Depends(get_db)
):
    """Admin endpoint: upload a PDF file, process it, and store embeddings in Pinecone."""

    # Validate file type
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Chỉ chấp nhận file PDF.")

    # Validate file size (max 20MB)
    MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=f"File quá lớn. Tối đa {MAX_FILE_SIZE // (1024*1024)}MB.")

    # Save uploaded file to a temp location
    tmp_path = ""
    try:
        fd, tmp_path = tempfile.mkstemp(suffix=".pdf")
        with os.fdopen(fd, "wb") as f:
            f.write(content)
        
        # Process PDF: extract text, chunk, create embeddings
        processor = PDFProcessorService()

        # Generate document_id early so Pinecone and MongoDB share the same key
        short_id = uuid.uuid4().hex[:6]
        document_id = f"doc_{ticker.lower().strip()}_{year}_{short_id}"

        metadata = {
            "ticker": ticker.upper().strip(),
            "doc_type": doc_type,
            "period": period,
            "year": int(year) if year.isdigit() else year,
            "source": file.filename
        }

        chunks = processor.process_and_chunk_pdf(tmp_path, metadata, document_id=document_id)

        if not chunks:
            raise HTTPException(status_code=400, detail="Không trích xuất được nội dung từ file PDF.")

        # Validate chunks: ensure no empty or broken chunks
        valid_chunks = [
            c for c in chunks
            if c.get("text") and len(c.get("text", "").strip()) > 10
        ]

        if len(valid_chunks) < len(chunks):
            logger.warning(
                f"PDF validation: {len(chunks) - len(valid_chunks)} broken chunks removed from {file.filename}. "
                f"Valid chunks: {len(valid_chunks)}"
            )

        if not valid_chunks:
            raise HTTPException(
                status_code=400,
                detail="File PDF không chứa nội dung hợp lệ (nội dung quá ngắn hoặc trống)."
            )

        chunks = valid_chunks
        
        # Upsert chunks to Pinecone (dùng singleton vector_store)
        success = vector_store.upsert_chunks(chunks)

        if not success:
            raise HTTPException(status_code=500, detail="Lỗi khi lưu vào vector store. Kiểm tra Pinecone API key.")

        indexed_at = datetime.datetime.utcnow().isoformat()

        # Save document record to MongoDB
        doc_record = {
            "document_id": document_id,
            "filename": file.filename,
            "ticker": ticker.upper().strip(),
            "doc_type": doc_type,
            "period": period,
            "year": int(year) if year.isdigit() else year,
            "chunks_count": len(chunks),
            "vector_store": "pinecone",
            "namespace": settings.PINECONE_INDEX_NAME,
            "embedding_model": "paraphrase-multilingual-MiniLM-L12-v2",
            "index_version": 1,
            "status": "indexed",
            "uploaded_by": current_user.username,
            "uploaded_at": datetime.datetime.utcnow().isoformat(),
            "indexed_at": indexed_at,
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
                "document_id": document_id,
                "filename": file.filename,
                "ticker": ticker.upper().strip(),
                "doc_type": doc_type,
                "period": period,
                "year": doc_record["year"],
                "chunks_count": len(chunks),
                "vector_store": "pinecone",
                "namespace": settings.PINECONE_INDEX_NAME,
                "embedding_model": "paraphrase-multilingual-MiniLM-L12-v2",
                "index_version": 1,
                "status": "indexed",
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
    vector_store: VectorStoreService = Depends(get_vector_store),
    db=Depends(get_db)
):
    """Delete a document record and its vectors from Pinecone."""
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")

    # Validate ObjectId format
    try:
        obj_id = ObjectId(doc_id)
    except Exception:
        raise HTTPException(status_code=400, detail="ID tài liệu không hợp lệ")

    try:
        # Lấy thông tin document trước khi xóa (để biết source filename)
        doc = await db["knowledge_base"].find_one({"_id": obj_id})
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        # Xóa vectors trong Pinecone: ưu tiên theo document_id, fallback về source filename
        doc_id_field = doc.get("document_id")
        source_filename = doc.get("filename")
        if doc_id_field:
            vector_store.delete_by_metadata({"document_id": doc_id_field})
        elif source_filename:
            vector_store.delete_by_metadata({"source": source_filename})

        # Xóa record trong MongoDB
        await db["knowledge_base"].delete_one({"_id": obj_id})

        logger.info(f"Document {doc_id} + vectors deleted by {current_user.username}")
        return {"status": "success", "message": "Đã xóa tài liệu và vectors"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete document: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ─── Backfill Missing Fields (Admin Only) ────────────────────────────────────
@router.patch("/documents/backfill/")
async def backfill_documents(
    current_user: User = Depends(check_admin_role),
    db=Depends(get_db)
):
    """Backfill missing fields for old document records in knowledge_base."""
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")

    try:
        # Find documents missing any of the required fields
        cursor = db["knowledge_base"].find({
            "$or": [
                {"document_id": {"$exists": False}},
                {"vector_store": {"$exists": False}},
                {"namespace": {"$exists": False}},
                {"status": {"$exists": False}},
                {"embedding_model": {"$exists": False}},
                {"index_version": {"$exists": False}},
                {"indexed_at": {"$exists": False}},
            ]
        })

        updated_count = 0
        async for doc in cursor:
            ticker = doc.get("ticker", "unknown").lower()
            year = doc.get("year", "2024")
            short_id = uuid.uuid4().hex[:6]

            update_fields = {}
            if "document_id" not in doc:
                update_fields["document_id"] = f"doc_{ticker}_{year}_{short_id}"
            if "vector_store" not in doc:
                update_fields["vector_store"] = "pinecone"
            if "namespace" not in doc:
                update_fields["namespace"] = settings.PINECONE_INDEX_NAME
            if "embedding_model" not in doc:
                update_fields["embedding_model"] = "paraphrase-multilingual-MiniLM-L12-v2"
            if "index_version" not in doc:
                update_fields["index_version"] = 1
            if "status" not in doc:
                update_fields["status"] = "indexed"
            if "indexed_at" not in doc:
                update_fields["indexed_at"] = doc.get("uploaded_at", datetime.datetime.utcnow().isoformat())
            # Convert year string to int if needed
            if isinstance(doc.get("year"), str) and doc["year"].isdigit():
                update_fields["year"] = int(doc["year"])

            if update_fields:
                await db["knowledge_base"].update_one(
                    {"_id": doc["_id"]},
                    {"$set": update_fields}
                )
                updated_count += 1

        return {
            "status": "success",
            "message": f"Đã cập nhật {updated_count} document(s)",
            "updated_count": updated_count,
        }
    except Exception as e:
        logger.error(f"Backfill failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ─── Chat History Endpoints ──────────────────────────────────────────────────

class SaveChatRequest(BaseModel):
    messages: List[ChatMessage] = Field(..., max_length=200, description="Danh sách messages")

@router.post("/chat/save")
async def save_chat_history(
    request: SaveChatRequest,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db)
):
    """Save current chat session to MongoDB."""
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")

    try:
        session_data = {
            "user_id": current_user.username,
            "messages": [{"role": m.role, "content": m.content} for m in request.messages],
            "message_count": len(request.messages),
            "updated_at": datetime.datetime.utcnow().isoformat(),
        }

        # Upsert: 1 session per user (overwrite)
        await db["chat_sessions"].update_one(
            {"user_id": current_user.username},
            {"$set": session_data},
            upsert=True
        )
        return {"status": "success", "message_count": len(request.messages)}
    except Exception as e:
        logger.error(f"Save chat failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/chat/history")
async def get_chat_history(
    current_user: User = Depends(get_current_user),
    db=Depends(get_db)
):
    """Load saved chat session from MongoDB."""
    if db is None:
        return {"messages": []}

    try:
        session = await db["chat_sessions"].find_one({"user_id": current_user.username})
        if not session:
            return {"messages": []}
        return {"messages": session.get("messages", []), "updated_at": session.get("updated_at")}
    except Exception as e:
        logger.error(f"Load chat failed: {e}")
        return {"messages": []}

@router.delete("/chat/history")
async def clear_chat_history(
    current_user: User = Depends(get_current_user),
    db=Depends(get_db)
):
    """Clear saved chat session."""
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")

    await db["chat_sessions"].delete_one({"user_id": current_user.username})
    return {"status": "success", "message": "Đã xóa lịch sử chat"}
