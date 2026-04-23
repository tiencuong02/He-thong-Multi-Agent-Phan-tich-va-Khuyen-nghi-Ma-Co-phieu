"""
RAG Pipeline — Advanced Agentic RAG với multi-pipeline architecture.

Flow mỗi query:
  1. Input Guard     — validate, sanitize, detect injection
  2. Intent Router   — phân loại ADVISORY / KNOWLEDGE / COMPLAINT / OUT_OF_SCOPE
  3. Pipeline Select — chọn pipeline phù hợp với intent
  4. Retrieve        — Hybrid Search (BGE-M3 + BM25) + Cross-encoder Rerank
  5. CRAG Eval       — self-evaluate relevance của docs
  6. Generate        — LLM generate với context đã lọc
  7. Output Guard    — confidence gate + disclaimer injection + hallucination check
  8. Audit Log       — ghi log mọi bước để compliance
"""

import logging
import time
import asyncio
from typing import Dict, Any, List, Optional, AsyncGenerator

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from app.services.rag.vector_store import VectorStoreService
from app.services.rag.intent_router import IntentRouter, Intent, IntentResult
from app.services.rag.guardrails import (
    InputGuard, RetrievalGuard, OutputGuard, CRAGEvaluator,
    INSUFFICIENT_DOCS_RESPONSE, OUT_OF_SCOPE_RESPONSE,
    ESCALATION_RESPONSE, ADVISORY_DISCLAIMER,
)
from app.core.config import settings

logger = logging.getLogger(__name__)

GEMINI_MODELS = ["gemini-2.5-flash", "gemini-2.5-flash-lite"]

# ─── System prompts theo từng pipeline ───────────────────────────────────────

_ADVISORY_SYSTEM = """Bạn là chuyên gia tư vấn đầu tư chứng khoán của hệ thống.

QUY TẮC BẮT BUỘC:
1. CHỈ sử dụng thông tin từ phần "Ngữ cảnh" được cung cấp — KHÔNG tự sáng tác
2. Nếu ngữ cảnh KHÔNG đủ để trả lời, nói rõ: "Tôi không có đủ thông tin từ tài liệu để tư vấn về vấn đề này"
3. KHÔNG bao giờ đưa ra con số cụ thể (giá mục tiêu, %, tỷ suất) nếu không có trong tài liệu
4. Luôn trích dẫn nguồn: "Theo [tên tài liệu], trang X..."
5. Trình bày rõ ràng: phân tích → rủi ro → kết luận — định dạng markdown

Trả lời bằng tiếng Việt, chuyên nghiệp, súc tích."""

_KNOWLEDGE_SYSTEM = """Bạn là chuyên gia kiến thức tài chính và chứng khoán.

QUY TẮC:
1. Ưu tiên thông tin từ "Ngữ cảnh" nếu có
2. Có thể bổ sung kiến thức chung nhưng phải ghi rõ "(Kiến thức chung)"
3. Với câu hỏi pháp luật: trích dẫn điều khoản cụ thể nếu có trong tài liệu
4. Giải thích đơn giản, dễ hiểu, có ví dụ minh hoạ khi cần
5. Định dạng markdown rõ ràng

Trả lời bằng tiếng Việt."""

_COMPLAINT_SYSTEM = """Bạn là nhân viên hỗ trợ khách hàng của công ty chứng khoán.

QUY TẮC:
1. Lắng nghe và đồng cảm với vấn đề của khách hàng
2. Tra cứu FAQ để đưa ra hướng dẫn cụ thể
3. Nếu vấn đề phức tạp → hướng dẫn liên hệ trực tiếp
4. KHÔNG hứa hẹn điều gì ngoài phạm vi FAQ
5. Luôn lịch sự và chuyên nghiệp

Trả lời bằng tiếng Việt."""

_FALLBACK_SYSTEM = """Bạn là trợ lý tài chính AI.
Hệ thống KHÔNG có tài liệu liên quan đến câu hỏi này.
Luôn bắt đầu bằng: "⚠️ Lưu ý: Câu trả lời dưới đây dựa trên kiến thức chung, không phải tài liệu chính thức."
Trả lời ngắn gọn bằng tiếng Việt."""


class RAGPipelineService:
    def __init__(self, vector_store: VectorStoreService):
        self.vector_store = vector_store
        self.llm: Optional[Any] = None
        self.llm_fallbacks: List[Any] = []

        # Guards & router
        self._input_guard      = InputGuard()
        self._retrieval_guard  = RetrievalGuard()
        self._output_guard     = OutputGuard()
        self._intent_router: Optional[IntentRouter] = None  # init sau khi có llm
        self._crag: Optional[CRAGEvaluator] = None

        self._init_llm()

    def _init_llm(self):
        if not settings.GEMINI_API_KEY:
            logger.warning("GEMINI_API_KEY not set — RAG pipeline disabled.")
            return

        initialized = []
        for model_name in GEMINI_MODELS:
            try:
                llm = ChatGoogleGenerativeAI(
                    model=model_name,
                    google_api_key=settings.GEMINI_API_KEY,
                    temperature=0.1,   # thấp hơn → ít hallucinate hơn
                    convert_system_message_to_human=True,
                )
                initialized.append((model_name, llm))
            except Exception as e:
                logger.warning(f"Cannot init {model_name}: {e}")

        if not initialized:
            logger.error("No Gemini model available.")
            return

        _, self.llm = initialized[0]
        self.llm_fallbacks = [llm for _, llm in initialized[1:]]
        logger.info(f"LLMs ready: {[n for n, _ in initialized]}")

        # Init router và CRAG sau khi có LLM
        self._intent_router = IntentRouter(llm=self.llm)
        self._crag = CRAGEvaluator(llm=self.llm)

    def _is_ready(self) -> bool:
        return self.llm is not None

    def _prewarm(self):
        try:
            self.vector_store.embeddings.embed_query("warmup")
            logger.info("Embedding model pre-warmed.")
        except Exception as e:
            logger.warning(f"Prewarm failed: {e}")

    # ─── LLM invocation với fallback ────────────────────────────────────────

    def _is_retryable(self, err: str) -> bool:
        err_l = err.lower()
        if any(x in err for x in ("404", "401")):
            return False
        if any(x in err for x in ("not found", "unauthorized")):
            return False
        return any(x in err_l for x in (
            "503", "429", "quota", "resource_exhausted",
            "unavailable", "overloaded", "rate limit", "too many",
        ))

    async def _invoke(self, messages: list) -> str:
        for idx, llm in enumerate([self.llm] + self.llm_fallbacks):
            if llm is None:
                continue
            try:
                result = await llm.ainvoke(messages)
                return result.content if hasattr(result, "content") else str(result)
            except Exception as e:
                if self._is_retryable(str(e)):
                    continue
                raise
        raise Exception("All Gemini models unavailable.")

    async def _stream(self, messages: list) -> AsyncGenerator[str, None]:
        for idx, llm in enumerate([self.llm] + self.llm_fallbacks):
            if llm is None:
                continue
            try:
                async for chunk in llm.astream(messages):
                    text = chunk.content if hasattr(chunk, "content") else str(chunk)
                    if text:
                        yield text
                return
            except Exception as e:
                if self._is_retryable(str(e)):
                    continue
                raise
        yield "Tất cả Gemini models đang quá tải. Vui lòng thử lại sau."

    # ─── Build message list với conversation history ─────────────────────────

    @staticmethod
    def _build_messages(
        system: str,
        context: str,
        query: str,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> list:
        msgs = [SystemMessage(content=system)]
        if history:
            for msg in history[-8:]:  # giữ 8 turns gần nhất
                if msg["role"] == "user":
                    msgs.append(HumanMessage(content=msg["content"]))
                else:
                    msgs.append(AIMessage(content=msg["content"]))
        user_content = f"Ngữ cảnh:\n{context}\n\nCâu hỏi: {query}" if context else query
        msgs.append(HumanMessage(content=user_content))
        return msgs

    @staticmethod
    def _format_context(docs: List[Any]) -> str:
        """Format docs — dùng parent_text nếu có (Small-to-Big), fallback về page_content."""
        parts = []
        for doc in docs:
            # Lấy parent_text từ metadata nếu hierarchical chunking đã tạo
            content = doc.metadata.get("parent_text") or doc.page_content
            source = doc.metadata.get("source", "Unknown")
            page   = doc.metadata.get("page", "?")
            parts.append(f"[Nguồn: {source}, Trang {page}]\n{content}")
        return "\n\n---\n\n".join(parts)

    @staticmethod
    def _extract_sources(docs: List[Any]) -> List[Dict[str, Any]]:
        seen, sources = set(), []
        for doc in docs:
            key = (doc.metadata.get("source", ""), doc.metadata.get("page", ""))
            if key not in seen:
                seen.add(key)
                sources.append({
                    "source":   doc.metadata.get("source", "Unknown"),
                    "page":     doc.metadata.get("page", "?"),
                    "doc_type": doc.metadata.get("doc_type", "Tài liệu"),
                    "period":   doc.metadata.get("period", ""),
                    "ticker":   doc.metadata.get("ticker", ""),
                })
        return sources

    # ─── Ticker extraction ───────────────────────────────────────────────────

    def _extract_tickers_multi(self, query: str) -> List[str]:
        import re
        STOPWORDS = {
            "KHÔNG","THEO","TRONG","NĂM","QUÝ","VÀ","CỦA","CHO","LÀ","CÓ",
            "BÁO","CÁO","TÔI","MÃ","CỔ","PHIẾU","PHÂN","TÍCH","VỀ","HỎI",
            "BIẾT","THE","FOR","AND","NHÀ","ĐẦU","TƯ","SO","SÁNH","VỚI",
            "VS","HAY","COMPARE","NÊN","MUA","BÁN","GIỮ",
        }
        tokens = re.findall(r'\b[A-Z]{2,5}\b', query.upper())
        seen, result = set(), []
        for t in tokens:
            if t not in STOPWORDS and t not in seen:
                seen.add(t)
                result.append(t)
        return result[:3]

    async def _extract_ticker(self, query: str) -> Optional[str]:
        import re
        STOPWORDS = {
            "KHÔNG","THEO","TRONG","NĂM","QUÝ","VÀ","CỦA","CHO","LÀ","CÓ",
            "BÁO","CÁO","TÔI","MÃ","CỔ","PHIẾU","PHÂN","TÍCH","VỀ","HỎI",
            "BIẾT","THE","FOR","AND","NHÀ","ĐẦU","TƯ",
        }
        kw_match = re.search(
            r'(?:m[aã]\b|c[oổồ]\s*phi[eếề]u\b|ph[aâ]n\s*t[íi]ch\b|'
            r'v[eề]\b|c[uủ]a\b|h[oỏ]i\s*v[eề]\b|b[aá]o\s*c[aá]o\b)'
            r'\s+([A-Z]{2,5})(?!\w)',
            query, re.IGNORECASE,
        )
        if kw_match:
            t = kw_match.group(1).upper()
            if t not in STOPWORDS:
                return t

        if not self.llm:
            return None
        try:
            result = await self._invoke([HumanMessage(
                content=(
                    "Extract the Vietnamese stock ticker symbol from this query. "
                    "Output ONLY the ticker (e.g. FPT, VNM) or NONE.\n"
                    f"Query: {query}"
                )
            )])
            result = result.strip().upper()
            return None if result in ("NONE", "") or len(result) > 5 else result
        except Exception:
            return None

    # ─── Advisory Pipeline ───────────────────────────────────────────────────

    async def _advisory_answer(
        self,
        query: str,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        ticker = await self._extract_ticker(query)
        filter_meta = {"ticker": ticker} if ticker else {}

        # Retrieve từ namespace advisory
        docs = self.vector_store.search_advisory(query, k=5, filter_metadata=filter_meta)

        # Retrieval Guard
        rg = self._retrieval_guard.check_advisory(docs)
        if not rg.passed:
            return {
                "answer": INSUFFICIENT_DOCS_RESPONSE,
                "intent": Intent.ADVISORY,
                "ticker_identified": ticker,
                "sources": [],
                "confidence": 0.0,
                "crag_status": "INCORRECT",
            }

        # CRAG evaluation
        crag_status = await self._crag.evaluate(query, rg.filtered_docs)
        if crag_status == CRAGEvaluator.INCORRECT:
            return {
                "answer": INSUFFICIENT_DOCS_RESPONSE,
                "intent": Intent.ADVISORY,
                "ticker_identified": ticker,
                "sources": [],
                "confidence": 0.0,
                "crag_status": crag_status,
            }

        context = self._format_context(rg.filtered_docs)
        messages = self._build_messages(_ADVISORY_SYSTEM, context, query, history)

        start = time.time()
        raw_answer = await self._invoke(messages)
        logger.info(f"Advisory LLM: {time.time()-start:.2f}s")

        # Output Guard
        og = self._output_guard.check_advisory(
            raw_answer, rg.quality_score, len(rg.filtered_docs)
        )

        return {
            "answer":           og.final_answer,
            "intent":           Intent.ADVISORY,
            "ticker_identified": ticker,
            "sources":          self._extract_sources(rg.filtered_docs),
            "confidence":       og.confidence,
            "crag_status":      crag_status,
            "disclaimer_injected": og.disclaimer_injected,
        }

    async def _advisory_stream(
        self,
        query: str,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        ticker = await self._extract_ticker(query)
        yield {"type": "ticker", "content": ticker}

        filter_meta = {"ticker": ticker} if ticker else {}
        docs = self.vector_store.search_advisory(query, k=5, filter_metadata=filter_meta)

        rg = self._retrieval_guard.check_advisory(docs)
        if not rg.passed:
            yield {"type": "error", "content": INSUFFICIENT_DOCS_RESPONSE}
            return

        crag_status = await self._crag.evaluate(query, rg.filtered_docs)
        yield {"type": "crag_status", "content": crag_status}

        if crag_status == CRAGEvaluator.INCORRECT:
            yield {"type": "error", "content": INSUFFICIENT_DOCS_RESPONSE}
            return

        yield {"type": "sources", "content": self._extract_sources(rg.filtered_docs)}

        context = self._format_context(rg.filtered_docs)
        messages = self._build_messages(_ADVISORY_SYSTEM, context, query, history)

        full_answer = ""
        async for token in self._stream(messages):
            full_answer += token
            yield {"type": "token", "content": token}

        # Output guard check (post-stream)
        og = self._output_guard.check_advisory(
            full_answer, rg.quality_score, len(rg.filtered_docs)
        )
        if not og.passed:
            # Đã stream rồi, gửi override message
            yield {"type": "override", "content": og.final_answer}
        elif og.disclaimer_injected:
            yield {"type": "disclaimer", "content": ADVISORY_DISCLAIMER}

        yield {"type": "confidence", "content": og.confidence}

    # ─── Knowledge Pipeline ──────────────────────────────────────────────────

    async def _knowledge_answer(
        self,
        query: str,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        ticker = await self._extract_ticker(query)
        filter_meta = {"ticker": ticker} if ticker else {}

        docs = self.vector_store.search_knowledge(query, k=5, filter_metadata=filter_meta)

        rg = self._retrieval_guard.check_knowledge(docs)
        context = self._format_context(rg.filtered_docs) if rg.filtered_docs else ""
        system  = _KNOWLEDGE_SYSTEM if rg.filtered_docs else _FALLBACK_SYSTEM

        messages = self._build_messages(system, context, query, history)
        raw_answer = await self._invoke(messages)

        og = self._output_guard.check_knowledge(
            raw_answer, rg.quality_score, len(rg.filtered_docs)
        )
        return {
            "answer":           og.final_answer,
            "intent":           Intent.KNOWLEDGE,
            "ticker_identified": ticker,
            "sources":          self._extract_sources(rg.filtered_docs),
            "confidence":       og.confidence,
        }

    async def _knowledge_stream(
        self,
        query: str,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        ticker = await self._extract_ticker(query)
        yield {"type": "ticker", "content": ticker}

        filter_meta = {"ticker": ticker} if ticker else {}
        docs = self.vector_store.search_knowledge(query, k=5, filter_metadata=filter_meta)

        rg = self._retrieval_guard.check_knowledge(docs)
        if rg.filtered_docs:
            yield {"type": "sources", "content": self._extract_sources(rg.filtered_docs)}

        context = self._format_context(rg.filtered_docs) if rg.filtered_docs else ""
        system  = _KNOWLEDGE_SYSTEM if rg.filtered_docs else _FALLBACK_SYSTEM
        messages = self._build_messages(system, context, query, history)

        async for token in self._stream(messages):
            yield {"type": "token", "content": token}

    # ─── Complaint Pipeline ──────────────────────────────────────────────────

    async def _complaint_answer(
        self,
        query: str,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        docs = self.vector_store.search_faq(query, k=3)
        rg = self._retrieval_guard.check_complaint(docs)

        context = self._format_context(rg.filtered_docs) if rg.filtered_docs else ""
        messages = self._build_messages(_COMPLAINT_SYSTEM, context, query, history)
        raw_answer = await self._invoke(messages)

        og = self._output_guard.check_complaint(raw_answer)
        return {
            "answer":    og.final_answer,
            "intent":    Intent.COMPLAINT,
            "sources":   self._extract_sources(rg.filtered_docs),
            "confidence": og.confidence,
        }

    async def _complaint_stream(
        self,
        query: str,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        docs = self.vector_store.search_faq(query, k=3)
        rg = self._retrieval_guard.check_complaint(docs)

        if rg.filtered_docs:
            yield {"type": "sources", "content": self._extract_sources(rg.filtered_docs)}

        context = self._format_context(rg.filtered_docs) if rg.filtered_docs else ""
        messages = self._build_messages(_COMPLAINT_SYSTEM, context, query, history)

        async for token in self._stream(messages):
            yield {"type": "token", "content": token}

    # ─── Public API ──────────────────────────────────────────────────────────

    async def answer_query(
        self,
        query: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        if not self._is_ready():
            return {
                "answer": "Hệ thống RAG chưa sẵn sàng. Kiểm tra GEMINI_API_KEY.",
                "sources": [],
            }

        # Input Guard
        ig = self._input_guard.check(query)
        if not ig.passed:
            return {"answer": ig.rejection_reason, "sources": [], "confidence": 0.0}

        # Intent classification
        intent_result: IntentResult = await self._intent_router.classify_with_llm(ig.sanitized_query)
        logger.info(
            f"Intent: {intent_result.intent} (conf={intent_result.confidence:.2f}) "
            f"| Query: '{ig.sanitized_query[:60]}'"
        )

        if intent_result.needs_clarification:
            return {
                "answer": IntentRouter.get_clarification_message(ig.sanitized_query),
                "intent": "UNCLEAR",
                "sources": [],
                "confidence": intent_result.confidence,
            }

        query_clean = ig.sanitized_query

        if intent_result.intent == Intent.OUT_OF_SCOPE:
            return {"answer": OUT_OF_SCOPE_RESPONSE, "intent": Intent.OUT_OF_SCOPE, "sources": []}

        if intent_result.intent == Intent.ADVISORY:
            return await self._advisory_answer(query_clean, conversation_history)

        if intent_result.intent == Intent.COMPLAINT:
            return await self._complaint_answer(query_clean, conversation_history)

        # Default: KNOWLEDGE
        return await self._knowledge_answer(query_clean, conversation_history)

    async def answer_query_stream(
        self,
        query: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        if not self._is_ready():
            yield {"type": "error", "content": "Hệ thống RAG chưa sẵn sàng."}
            return

        # Input Guard
        ig = self._input_guard.check(query)
        if not ig.passed:
            yield {"type": "error", "content": ig.rejection_reason}
            return

        # Intent
        intent_result = await self._intent_router.classify_with_llm(ig.sanitized_query)
        yield {"type": "intent", "content": intent_result.intent}
        logger.info(f"Stream Intent: {intent_result.intent} | '{ig.sanitized_query[:60]}'")

        if intent_result.needs_clarification:
            yield {"type": "token", "content": IntentRouter.get_clarification_message(ig.sanitized_query)}
            return

        if intent_result.intent == Intent.OUT_OF_SCOPE:
            yield {"type": "token", "content": OUT_OF_SCOPE_RESPONSE}
            return

        query_clean = ig.sanitized_query

        if intent_result.intent == Intent.ADVISORY:
            async for chunk in self._advisory_stream(query_clean, conversation_history):
                yield chunk
            return

        if intent_result.intent == Intent.COMPLAINT:
            async for chunk in self._complaint_stream(query_clean, conversation_history):
                yield chunk
            return

        async for chunk in self._knowledge_stream(query_clean, conversation_history):
            yield chunk

    # ─── Multi-ticker comparison ─────────────────────────────────────────────

    async def compare_tickers_stream(
        self,
        query: str,
        tickers: List[str],
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        if not self._is_ready():
            yield {"type": "error", "content": "Hệ thống RAG chưa sẵn sàng."}
            return

        ig = self._input_guard.check(query)
        if not ig.passed:
            yield {"type": "error", "content": ig.rejection_reason}
            return

        tickers = tickers[:3]
        if len(tickers) < 2:
            yield {"type": "error", "content": "Cần ít nhất 2 mã cổ phiếu để so sánh."}
            return

        yield {"type": "tickers", "content": tickers}

        # Retrieve docs cho mỗi ticker song song
        async def fetch(ticker: str):
            try:
                docs = await asyncio.to_thread(
                    self.vector_store.search_advisory,
                    ig.sanitized_query, 4, {"ticker": ticker},
                )
                return ticker, docs
            except Exception as e:
                logger.error(f"Compare fetch {ticker}: {e}")
                return ticker, []

        results = await asyncio.gather(*[fetch(t) for t in tickers])
        docs_by_ticker = dict(results)

        sources_by_ticker = {
            t: self._extract_sources(docs_by_ticker.get(t, []))
            for t in tickers
        }
        yield {"type": "sources", "content": sources_by_ticker}

        # Build context per ticker
        parts = []
        for t in tickers:
            docs = docs_by_ticker.get(t, [])
            if not docs:
                parts.append(f"=== {t} ===\nKhông có dữ liệu cho {t} trong hệ thống.")
            else:
                rg = self._retrieval_guard.check_advisory(docs)
                parts.append(f"=== {t} ===\n{self._format_context(rg.filtered_docs)}")

        context = "\n\n---\n\n".join(parts)
        system = (
            "Bạn là chuyên gia phân tích tài chính. So sánh các mã cổ phiếu DỰA HOÀN TOÀN "
            "trên tài liệu. Trình bày bảng markdown với các tiêu chí tài chính quan trọng. "
            "Sau bảng viết 2-3 câu nhận xét. CHỈ dùng thông tin trong ngữ cảnh. "
            "Thiếu dữ liệu ghi N/A. Trả lời bằng tiếng Việt."
        )
        messages = self._build_messages(system, context, ig.sanitized_query, conversation_history)

        full_answer = ""
        async for token in self._stream(messages):
            full_answer += token
            yield {"type": "token", "content": token}

        yield {"type": "disclaimer", "content": ADVISORY_DISCLAIMER}
