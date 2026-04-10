import logging
import re
import time
from typing import Dict, Any, List, Optional, AsyncGenerator
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.services.rag.vector_store import VectorStoreService
from app.core.config import settings

logger = logging.getLogger(__name__)

GEMINI_MODELS = ["gemini-2.5-flash", "gemini-2.5-flash-lite"]

class RAGPipelineService:
    def __init__(self, vector_store: VectorStoreService):
        self.vector_store = vector_store
        self.llm = None
        self.llm_fallbacks: List[Any] = []

        if not settings.GEMINI_API_KEY:
            logger.warning("RAG: GEMINI_API_KEY not set. Check your .env file.")
            return

        # Init primary + fallback models
        initialized = []
        for model_name in GEMINI_MODELS:
            try:
                llm = ChatGoogleGenerativeAI(
                    model=model_name,
                    google_api_key=settings.GEMINI_API_KEY,
                    temperature=0.2,
                    convert_system_message_to_human=True,
                )
                initialized.append((model_name, llm))
            except Exception as e:
                logger.warning(f"RAG: Could not init {model_name}: {e}")

        if initialized:
            primary_name, self.llm = initialized[0]
            self.llm_fallbacks = [llm for _, llm in initialized[1:]]
            fallback_names = [n for n, _ in initialized[1:]]
            logger.info(f"RAG: Primary={primary_name}, fallbacks={fallback_names}")
        else:
            logger.error("RAG: Failed to initialize any Gemini model.")

    def _is_retryable_error(self, err_str: str) -> bool:
        """Kiểm tra lỗi có nên retry fallback không (503, 429, overload)."""
        err_lower = err_str.lower()
        # 404 NOT_FOUND không phải lỗi tạm thời — model không tồn tại
        if "404" in err_str or "not found" in err_lower or "not_found" in err_lower:
            return False
        # 401 UNAUTHORIZED — auth error, không nên retry
        if "401" in err_str or "unauthorized" in err_lower:
            return False
        # Tất cả lỗi quota/rate limit là retryable
        return (
            "503" in err_str
            or "429" in err_str
            or "resource_exhausted" in err_lower
            or "quota" in err_lower
            or "unavailable" in err_lower
            or "overloaded" in err_lower
            or "high demand" in err_lower
            or "rate limit" in err_lower
            or "too many requests" in err_lower
        )

    async def _invoke_with_fallback(self, chain_factory, inputs) -> Any:
        """Try primary LLM, auto-fallback on 503/429/quota errors."""
        last_error = None
        quota_exhausted = False
        all_llms = [self.llm] + self.llm_fallbacks
        for idx, llm in enumerate(all_llms):
            if llm is None:
                continue
            model_name = getattr(llm, 'model', f'model_{idx}')
            try:
                chain = chain_factory(llm)
                result = await chain.ainvoke(inputs)
                logger.info(f"RAG invoke: success with {model_name}")
                return result
            except Exception as e:
                err_str = str(e)
                logger.error(f"RAG invoke: {model_name} failed [{type(e).__name__}]: {err_str[:300]}")
                if "429" in err_str or "quota" in err_str.lower():
                    quota_exhausted = True
                if self._is_retryable_error(err_str):
                    last_error = e
                    continue
                raise

        if quota_exhausted:
            raise Exception("Gemini API quota exhausted. Free tier limit exceeded. Please wait or upgrade your plan.")
        raise last_error or Exception("All Gemini models unavailable")

    def _is_ready(self) -> bool:
        return self.llm is not None

    def _prewarm(self):
        # Pre-warm the embedding model to avoid first-query hang
        try:
            logger.info("RAG: Pre-warming embedding model...")
            self.vector_store.embeddings.embed_query("warmup")
            logger.info("RAG: Embedding model ready.")
        except Exception as e:
            logger.warning(f"RAG: Failed to pre-warm embeddings: {e}")
        
    async def _extract_ticker_from_query(self, query: str) -> Optional[str]:
        """Extract the stock ticker symbol (if any) from the user query.
        Uses regex fast-path first to avoid an extra Gemini API call.
        """
        # Fast-path: explicit patterns — "mã FPT", "về VNM", "phân tích ACB", etc.
        # Works on both accented Vietnamese and ASCII-stripped forms.
        STOPWORDS = {
            "KHÔNG","THEO","TRONG","NĂM","QUÝ","VÀ","CỦA","CHO","LÀ","CÓ",
            "BÁO","CÁO","TÔI","MÃ","CỔ","PHIẾU","PHÂN","TÍCH","VỀ","HỎI",
            "BIẾT","THE","FOR","AND","NHÀ","ĐẦU","TƯ",
        }
        # Match ticker directly after common keywords (handles accented chars via [\w\s] lookahead)
        kw_match = re.search(
            r'(?:'
            r'm[aã]\b|'                       # mã / ma
            r'c[oổồ]\s*phi[eếề]u\b|'         # cổ phiếu
            r'ph[aâ]n\s*t[íi]ch\b|'          # phân tích
            r'v[eề]\b|'                        # về
            r'c[uủ]a\b|'                       # của
            r'h[oỏ]i\s*v[eề]\b|'             # hỏi về
            r'b[aá]o\s*c[aá]o\b'             # báo cáo
            r')\s+([A-Z]{2,5})(?!\w)',
            query,
            re.IGNORECASE
        )
        if kw_match:
            ticker = kw_match.group(1).upper().strip()
            if ticker not in STOPWORDS:
                return ticker

        # Slow-path: ask Gemini only when regex can't determine
        if not self.llm:
            return None

        extraction_prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a financial entity extractor. Extract the stock ticker symbol (e.g. FPT, VNM, HPG) from the user's query. If no ticker is found, simply output 'NONE'. Output ONLY the uppercase ticker symbol or 'NONE', nothing else. Typical Vietnamese syntax: 'phân tích mã ACB', 'cho tôi biết về FPT'."),
            ("user", "{query}")
        ])

        try:
            result = await self._invoke_with_fallback(
                lambda llm: extraction_prompt | llm | StrOutputParser(),
                {"query": query}
            )
            result = result.strip().upper()
            if result == "NONE" or len(result) > 5:
                return None
            return result
        except Exception as e:
            logger.error(f"Error extracting ticker: {e}")
            return None

    async def _fallback_answer(self, query: str, ticker: Optional[str], conversation_history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """Fallback: trả lời bằng kiến thức chung khi không có tài liệu RAG."""
        from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

        fallback_system = """Bạn là trợ lý tài chính AI. Hiện tại hệ thống KHÔNG có báo cáo tài chính nào liên quan trong cơ sở dữ liệu.
Hãy trả lời câu hỏi dựa trên kiến thức chung của bạn về tài chính, chứng khoán.
QUAN TRỌNG: Luôn bắt đầu câu trả lời bằng disclaimer:
"⚠️ **Lưu ý:** Câu trả lời dưới đây dựa trên kiến thức chung, KHÔNG phải từ báo cáo tài chính chính thức trong hệ thống."
Trả lời bằng tiếng Việt, ngắn gọn, hữu ích."""

        built_messages = [SystemMessage(content=fallback_system)]
        if conversation_history:
            for msg in conversation_history[-10:]:
                if msg["role"] == "user":
                    built_messages.append(HumanMessage(content=msg["content"]))
                else:
                    built_messages.append(AIMessage(content=msg["content"]))
        built_messages.append(HumanMessage(content=query))

        try:
            answer_msg = await self._invoke_with_fallback(
                lambda llm: llm,
                built_messages
            )
            answer = answer_msg.content if hasattr(answer_msg, "content") else str(answer_msg)
            return {
                "answer": answer,
                "ticker_identified": ticker,
                "sources": []
            }
        except Exception as e:
            logger.error(f"Fallback answer failed: {e}")
            return {
                "answer": "Xin lỗi, hiện tại hệ thống chưa có báo cáo tài chính nào liên quan và không thể tạo câu trả lời.",
                "ticker_identified": ticker,
                "sources": []
            }

    async def answer_query(self, query: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """
        Full RAG pipeline:
        1. Extract Ticker
        2. Retrieve Context (filtered by Ticker if found)
        3. Generate Answer (with conversation history for follow-up questions)
        """
        if not self._is_ready() or not self.vector_store or not self.vector_store.vector_store:
            return {
                "answer": "Hệ thống RAG chưa được cấu hình đầy đủ (Vui lòng kiểm tra GEMINI_API_KEY hoặc PINECONE_API_KEY trong .env).",
                "ticker_identified": None,
                "sources": []
            }

        ticker = await self._extract_ticker_from_query(query)
        
        filter_metadata = {}
        if ticker:
            filter_metadata["ticker"] = ticker
            logger.info(f"RAG: Extracted ticker '{ticker}' from query.")
            
        # Retrieve context from Vector Store
        logger.info(f"RAG: Searching for context in vector store...")
        docs = self.vector_store.search_similar_documents(query=query, k=5, filter_metadata=filter_metadata)
        logger.info(f"RAG: Found {len(docs)} relevant documents.")
        
        if not docs:
            logger.info("RAG: No relevant documents found. Falling back to general knowledge.")
            return await self._fallback_answer(query, ticker, conversation_history)
            
        # Format context
        context_text = "\n\n---\n\n".join([
            f"Source: {doc.metadata.get('source', 'Unknown')} (Page {doc.metadata.get('page', '?')})\nContent: {doc.page_content}" 
            for doc in docs
        ])
        
        # Generation Prompt - build messages with conversation history
        from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

        system_msg = """Bạn là một chuyên gia phân tích tài chính thông minh của hệ thống.
Bạn được cung cấp các đoạn trích từ báo cáo tài chính, báo cáo thường niên thực tế dưới phần 'Ngữ cảnh'.
Hãy sử dụng CHỈ CÁC THÔNG TIN TRONG NGỮ CẢNH để trả lời câu hỏi của người dùng.
Nếu ngữ cảnh không chứa đủ thông tin để trả lời, hãy nói rõ là "Tôi không có đủ thông tin từ báo cáo tài chính để trả lời chính xác".
ĐỪNG tự sáng tác thêm số liệu.
Trả lời bằng tiếng Việt, trình bày rõ ràng, dễ hiểu, định dạng markdown. Nếu có số liệu, hãy trích dẫn nguồn rõ ràng (VD: Theo Báo cáo tài chính quý 1, trang X...)."""

        built_messages = [SystemMessage(content=system_msg)]
        if conversation_history:
            for msg in conversation_history[-10:]:
                if msg["role"] == "user":
                    built_messages.append(HumanMessage(content=msg["content"]))
                else:
                    built_messages.append(AIMessage(content=msg["content"]))
        # Nối context thẳng vào HumanMessage — tránh hoàn toàn ChatPromptTemplate
        built_messages.append(HumanMessage(content=f"Ngữ cảnh:\n{context_text}\n\nCâu hỏi: {query}"))

        try:
            logger.info("RAG: Generating answer from LLM...")
            start_time = time.time()
            answer_msg = await self._invoke_with_fallback(
                lambda llm: llm,
                built_messages
            )
            answer = answer_msg.content if hasattr(answer_msg, "content") else str(answer_msg)
            duration = time.time() - start_time
            logger.info(f"RAG: LLM response received in {duration:.2f}s")
            
            # Extract sources for transparency
            sources = []
            for doc in docs:
                source_info = {
                    "source": doc.metadata.get('source', 'Unknown'),
                    "page": doc.metadata.get('page', '?'),
                    "doc_type": doc.metadata.get('doc_type', 'Báo cáo'),
                    "period": doc.metadata.get('period', '')
                }
                if source_info not in sources:
                    sources.append(source_info)
                    
            return {
                "answer": answer,
                "ticker_identified": ticker,
                "sources": sources
            }
        except Exception as e:
            logger.error(f"Error generating RAG answer: {type(e).__name__}: {str(e)[:200]}")
            return {
                "answer": "Đã xảy ra lỗi khi tạo câu trả lời. Vui lòng thử lại.",
                "ticker_identified": ticker,
                "sources": []
            }

    async def answer_query_stream(self, query: str, conversation_history: Optional[List[Dict[str, str]]] = None):
        """
        Streaming version of answer_query - yields chunks as they come from LLM.
        """
        if not self._is_ready() or not self.vector_store or not self.vector_store.vector_store:
            yield {"type": "error", "content": "Hệ thống RAG chưa được cấu hình đầy đủ."}
            return

        ticker = await self._extract_ticker_from_query(query)
        yield {"type": "ticker", "content": ticker}

        filter_metadata = {}
        if ticker:
            filter_metadata["ticker"] = ticker

        docs = self.vector_store.search_similar_documents(query=query, k=5, filter_metadata=filter_metadata)

        if not docs:
            # Fallback streaming
            async for chunk in self._fallback_stream(query, ticker, conversation_history):
                yield chunk
            return

        # Extract sources early
        sources = []
        for doc in docs:
            source_info = {
                "source": doc.metadata.get('source', 'Unknown'),
                "page": doc.metadata.get('page', '?'),
                "doc_type": doc.metadata.get('doc_type', 'Báo cáo'),
                "period": doc.metadata.get('period', '')
            }
            if source_info not in sources:
                sources.append(source_info)
        yield {"type": "sources", "content": sources}

        # Format context
        context_text = "\n\n---\n\n".join([
            f"Source: {doc.metadata.get('source', 'Unknown')} (Page {doc.metadata.get('page', '?')})\nContent: {doc.page_content}"
            for doc in docs
        ])

        system_msg = """Bạn là một chuyên gia phân tích tài chính thông minh của hệ thống.
Bạn được cung cấp các đoạn trích từ báo cáo tài chính, báo cáo thường niên thực tế dưới phần 'Ngữ cảnh'.
Hãy sử dụng CHỈ CÁC THÔNG TIN TRONG NGỮ CẢNH để trả lời câu hỏi của người dùng.
Nếu ngữ cảnh không chứa đủ thông tin để trả lời, hãy nói rõ là "Tôi không có đủ thông tin từ báo cáo tài chính để trả lời chính xác".
ĐỪNG tự sáng tác thêm số liệu.
Trả lời bằng tiếng Việt, trình bày rõ ràng, dễ hiểu, định dạng markdown."""

        from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

        built_messages = [SystemMessage(content=system_msg)]
        if conversation_history:
            for msg in conversation_history[-10:]:
                if msg["role"] == "user":
                    built_messages.append(HumanMessage(content=msg["content"]))
                else:
                    built_messages.append(AIMessage(content=msg["content"]))
        built_messages.append(HumanMessage(content=f"Ngữ cảnh:\n{context_text}\n\nCâu hỏi: {query}"))

        try:
            streamed = False
            for idx, llm in enumerate([self.llm] + self.llm_fallbacks):
                if llm is None:
                    continue
                model_name = getattr(llm, 'model', f'model_{idx}')
                try:
                    logger.info(f"RAG stream: trying {model_name}...")
                    async for chunk in llm.astream(built_messages):
                        text = chunk.content if hasattr(chunk, "content") else str(chunk)
                        if text:
                            yield {"type": "token", "content": text}
                    streamed = True
                    logger.info(f"RAG stream: success with {model_name}")
                    break
                except Exception as e:
                    err_str = str(e)
                    logger.error(f"RAG stream: {model_name} failed [{type(e).__name__}]: {err_str[:300]}")
                    if self._is_retryable_error(err_str):
                        logger.warning(f"RAG stream: retryable error, trying next model.")
                        continue
                    raise
            if not streamed:
                yield {"type": "error", "content": "Tất cả Gemini models đang quá tải. Vui lòng thử lại sau."}
        except Exception as e:
            logger.error(f"RAG stream (final catch): {type(e).__name__}: {str(e)[:300]}")
            yield {"type": "error", "content": "Đã xảy ra lỗi khi tạo câu trả lời. Vui lòng thử lại."}

    async def _fallback_stream(self, query: str, ticker: Optional[str], conversation_history: Optional[List[Dict[str, str]]] = None):
        """Streaming fallback khi không có tài liệu RAG."""
        fallback_system = """Bạn là trợ lý tài chính AI. Hiện tại hệ thống KHÔNG có báo cáo tài chính nào liên quan trong cơ sở dữ liệu.
Hãy trả lời câu hỏi dựa trên kiến thức chung của bạn về tài chính, chứng khoán.
QUAN TRỌNG: Luôn bắt đầu câu trả lời bằng disclaimer:
"⚠️ **Lưu ý:** Câu trả lời dưới đây dựa trên kiến thức chung, KHÔNG phải từ báo cáo tài chính chính thức trong hệ thống."
Trả lời bằng tiếng Việt, ngắn gọn, hữu ích."""

        from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

        built_messages = [SystemMessage(content=fallback_system)]
        if conversation_history:
            for msg in conversation_history[-10:]:
                if msg["role"] == "user":
                    built_messages.append(HumanMessage(content=msg["content"]))
                else:
                    built_messages.append(AIMessage(content=msg["content"]))
        built_messages.append(HumanMessage(content=query))

        try:
            streamed = False
            for idx, llm in enumerate([self.llm] + self.llm_fallbacks):
                if llm is None:
                    continue
                model_name = getattr(llm, 'model', f'model_{idx}')
                try:
                    logger.info(f"RAG fallback stream: trying {model_name}...")
                    async for chunk in llm.astream(built_messages):
                        text = chunk.content if hasattr(chunk, "content") else str(chunk)
                        if text:
                            yield {"type": "token", "content": text}
                    streamed = True
                    break
                except Exception as e:
                    err_str = str(e)
                    logger.error(f"RAG fallback stream: {model_name} failed [{type(e).__name__}]: {err_str[:300]}")
                    if self._is_retryable_error(err_str):
                        continue
                    raise
            if not streamed:
                yield {"type": "error", "content": "Tất cả Gemini models đang quá tải. Vui lòng thử lại sau."}
        except Exception as e:
            logger.error(f"RAG fallback stream (final): {type(e).__name__}: {str(e)[:300]}")
            yield {"type": "error", "content": "Đã xảy ra lỗi khi tạo câu trả lời. Vui lòng thử lại."}
