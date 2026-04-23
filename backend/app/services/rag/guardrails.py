"""
Guardrails — lớp kiểm soát đa tầng cho chatbot tư vấn tài chính.

3 tầng kiểm soát:
  INPUT  GUARD — validate query trước khi xử lý
  RETRIEVAL GUARD — kiểm tra chất lượng context retrieve được
  OUTPUT GUARD — kiểm tra câu trả lời trước khi trả về user

Nguyên tắc thiết kế:
  - Tư vấn đầu tư: sai là toi → guard chặt nhất
  - Thà từ chối lịch sự còn hơn đưa ra tư vấn sai
  - Mọi advisory response đều có mandatory disclaimer
  - Confidence thấp → escalate / từ chối, KHÔNG đoán mò
"""

import re
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Any

logger = logging.getLogger(__name__)

# ─── Disclaimer bắt buộc — inject vào MỌI advisory response ─────────────────

ADVISORY_DISCLAIMER = """
---
⚠️ **Lưu ý quan trọng:** Thông tin trên được tạo tự động từ tài liệu nội bộ và \
chỉ mang tính **tham khảo**. Đây **không phải** lời khuyên đầu tư chính thức. \
Kết quả đầu tư thực tế có thể khác biệt đáng kể. \
Vui lòng tham khảo chuyên gia tài chính có chứng chỉ trước khi ra quyết định đầu tư.
"""

LOW_CONFIDENCE_RESPONSE = (
    "Tôi không có đủ thông tin tin cậy từ tài liệu nội bộ để đưa ra tư vấn "
    "về vấn đề này một cách chính xác.\n\n"
    "Vui lòng liên hệ chuyên gia tài chính của chúng tôi để được hỗ trợ trực tiếp."
)

INSUFFICIENT_DOCS_RESPONSE = (
    "Hiện tại hệ thống chưa có đủ tài liệu liên quan đến nội dung bạn hỏi "
    "để đưa ra tư vấn đáng tin cậy.\n\n"
    "⚠️ Tư vấn đầu tư cần được dựa trên tài liệu chính thức. "
    "Vui lòng liên hệ bộ phận tư vấn để được hỗ trợ."
)

OUT_OF_SCOPE_RESPONSE = (
    "Xin lỗi, câu hỏi này nằm ngoài phạm vi hỗ trợ của tôi. "
    "Tôi chỉ có thể hỗ trợ về:\n"
    "- Tư vấn đầu tư chứng khoán\n"
    "- Kiến thức và quy định về chứng khoán\n"
    "- Hỗ trợ tài khoản giao dịch\n\n"
    "Vui lòng đặt câu hỏi liên quan đến lĩnh vực trên."
)

ESCALATION_RESPONSE = (
    "Câu hỏi này cần được xem xét bởi chuyên gia tài chính của chúng tôi "
    "để đảm bảo độ chính xác cao nhất.\n\n"
    "📞 Vui lòng liên hệ:\n"
    "- **Hotline:** 1800-xxx-xxx (miễn phí, 8h-17h các ngày làm việc)\n"
    "- **Email:** support@company.com\n"
    "- **Chat trực tiếp:** Nhấn nút 'Kết nối tư vấn viên' bên dưới."
)


# ─── Data classes ─────────────────────────────────────────────────────────────

@dataclass
class InputGuardResult:
    passed: bool
    rejection_reason: Optional[str] = None  # None nếu passed
    sanitized_query: str = ""               # query đã được làm sạch


@dataclass
class RetrievalGuardResult:
    passed: bool
    min_docs_met: bool
    quality_score: float          # 0.0-1.0, trung bình score của docs
    filtered_docs: List[Any] = field(default_factory=list)
    rejection_reason: Optional[str] = None


@dataclass
class OutputGuardResult:
    passed: bool
    confidence: float
    final_answer: str
    needs_escalation: bool = False
    disclaimer_injected: bool = False


# ─── Input Guard ──────────────────────────────────────────────────────────────

class InputGuard:
    """Kiểm tra và làm sạch query đầu vào."""

    MAX_QUERY_LENGTH = 800
    MIN_QUERY_LENGTH = 3

    # Prompt injection patterns
    _INJECTION_PATTERNS = [
        r"ignore (previous|above|all) instructions?",
        r"forget (everything|your instructions?|your role)",
        r"you are now",
        r"act as (a |an )?(different|new|another)",
        r"(system|assistant|user)\s*:",
        r"<\|?(system|user|assistant|im_start|im_end)\|?>",
        r"###\s*(instruction|system|prompt)",
        r"pretend (you are|to be)",
        r"disregard (your|the) (guidelines?|rules?|restrictions?)",
        r"reveal (your|the) (system prompt|instructions?|context)",
    ]

    _SENSITIVE_DATA_PATTERNS = [
        r"\b\d{9,12}\b",          # số tài khoản / CCCD dài
        r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b",  # số thẻ
        r"password|mật khẩu|passwd",
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # email
    ]

    def __init__(self):
        flags = re.IGNORECASE
        self._injection_re  = [re.compile(p, flags) for p in self._INJECTION_PATTERNS]
        self._sensitive_re  = [re.compile(p, flags) for p in self._SENSITIVE_DATA_PATTERNS]

    def check(self, query: str) -> InputGuardResult:
        q = query.strip()

        # Độ dài
        if len(q) < self.MIN_QUERY_LENGTH:
            return InputGuardResult(
                passed=False,
                rejection_reason="Câu hỏi quá ngắn.",
                sanitized_query=q,
            )
        if len(q) > self.MAX_QUERY_LENGTH:
            return InputGuardResult(
                passed=False,
                rejection_reason=f"Câu hỏi quá dài (tối đa {self.MAX_QUERY_LENGTH} ký tự).",
                sanitized_query=q,
            )

        # Prompt injection
        for pattern in self._injection_re:
            if pattern.search(q):
                logger.warning(f"Prompt injection detected: '{q[:80]}'")
                return InputGuardResult(
                    passed=False,
                    rejection_reason="Câu hỏi không hợp lệ. Vui lòng đặt câu hỏi rõ ràng.",
                    sanitized_query=q,
                )

        # Mask dữ liệu nhạy cảm
        sanitized = q
        for pattern in self._sensitive_re:
            sanitized = pattern.sub("[REDACTED]", sanitized)

        if sanitized != q:
            logger.info("InputGuard: sensitive data masked in query.")

        return InputGuardResult(passed=True, sanitized_query=sanitized)


# ─── Retrieval Guard ──────────────────────────────────────────────────────────

class RetrievalGuard:
    """Kiểm tra chất lượng của retrieved documents trước khi generate."""

    # Advisory: cần ít nhất 2 docs, tránh generate từ 1 nguồn duy nhất
    MIN_DOCS_ADVISORY  = 2
    MIN_DOCS_KNOWLEDGE = 1
    MIN_DOCS_COMPLAINT = 1

    def check_advisory(self, docs: List[Any]) -> RetrievalGuardResult:
        return self._check(docs, min_docs=self.MIN_DOCS_ADVISORY, label="ADVISORY")

    def check_knowledge(self, docs: List[Any]) -> RetrievalGuardResult:
        return self._check(docs, min_docs=self.MIN_DOCS_KNOWLEDGE, label="KNOWLEDGE")

    def check_complaint(self, docs: List[Any]) -> RetrievalGuardResult:
        return self._check(docs, min_docs=self.MIN_DOCS_COMPLAINT, label="COMPLAINT")

    @staticmethod
    def _check(docs: List[Any], min_docs: int, label: str) -> RetrievalGuardResult:
        valid_docs = [
            d for d in docs
            if d.page_content and len(d.page_content.strip()) >= 20
        ]
        min_met = len(valid_docs) >= min_docs

        if not valid_docs:
            return RetrievalGuardResult(
                passed=False,
                min_docs_met=False,
                quality_score=0.0,
                filtered_docs=[],
                rejection_reason=f"Không tìm thấy tài liệu liên quan ({label}).",
            )

        if not min_met:
            return RetrievalGuardResult(
                passed=False,
                min_docs_met=False,
                quality_score=0.5,
                filtered_docs=valid_docs,
                rejection_reason=(
                    f"Chỉ tìm thấy {len(valid_docs)}/{min_docs} tài liệu cần thiết ({label}). "
                    "Không đủ căn cứ để đưa ra tư vấn."
                ),
            )

        # Chấm quality score đơn giản dựa trên độ dài và đa dạng nguồn
        avg_len = sum(len(d.page_content) for d in valid_docs) / len(valid_docs)
        unique_sources = len({d.metadata.get("source", "") for d in valid_docs})
        quality = min(0.5 + (avg_len / 2000) * 0.3 + (unique_sources / 3) * 0.2, 1.0)

        return RetrievalGuardResult(
            passed=True,
            min_docs_met=True,
            quality_score=quality,
            filtered_docs=valid_docs,
        )


# ─── Output Guard ─────────────────────────────────────────────────────────────

class OutputGuard:
    """
    Kiểm tra câu trả lời từ LLM trước khi trả về user.
    Inject disclaimer, tính confidence, escalate nếu cần.
    """

    # Confidence gate — dưới ngưỡng này → từ chối hoặc escalate
    CONFIDENCE_GATE_ADVISORY  = 0.55
    CONFIDENCE_GATE_KNOWLEDGE = 0.40

    # Patterns nguy hiểm: LLM đang đoán mò
    _HALLUCINATION_SIGNALS = [
        r"tôi (không chắc|không biết chính xác|đoán|nghĩ rằng có thể)",
        r"có thể là|có lẽ là|chắc là",
        r"theo (tôi nghĩ|cảm giác của tôi|suy luận của tôi)",
        r"(tôi|mình) (tự|tự mình) (nghĩ|cho rằng|đoán)",
        r"không có trong (tài liệu|văn bản|dữ liệu).*(nhưng|tuy nhiên)",
    ]

    # Patterns cho thấy LLM đang bịa số liệu
    _FABRICATION_SIGNALS = [
        r"khoảng \d+[.,]\d+%",    # % estimate không từ doc
        r"ước tính (khoảng|tầm)",
        r"(có thể|có thể sẽ) (tăng|giảm) (khoảng|tầm|đến) \d+",
    ]

    def __init__(self):
        flags = re.IGNORECASE | re.UNICODE
        self._hallucination_re = [re.compile(p, flags) for p in self._HALLUCINATION_SIGNALS]
        self._fabrication_re   = [re.compile(p, flags) for p in self._FABRICATION_SIGNALS]

    def check_advisory(
        self,
        answer: str,
        retrieval_quality: float,
        num_docs: int,
    ) -> OutputGuardResult:
        """Advisory output — gate chặt nhất."""

        # Phát hiện hallucination signals
        hallucination_hits = sum(
            1 for p in self._hallucination_re if p.search(answer)
        )
        fabrication_hits = sum(
            1 for p in self._fabrication_re if p.search(answer)
        )

        # Tính confidence tổng hợp
        base_confidence = retrieval_quality
        if hallucination_hits > 0:
            base_confidence -= 0.15 * hallucination_hits
        if fabrication_hits > 0:
            base_confidence -= 0.20 * fabrication_hits
        if num_docs < 2:
            base_confidence -= 0.15
        confidence = max(0.0, min(base_confidence, 1.0))

        # Gate: confidence quá thấp → từ chối
        if confidence < self.CONFIDENCE_GATE_ADVISORY:
            logger.warning(
                f"OutputGuard ADVISORY blocked: confidence={confidence:.2f}, "
                f"hallucination_hits={hallucination_hits}, fabrication_hits={fabrication_hits}"
            )
            return OutputGuardResult(
                passed=False,
                confidence=confidence,
                final_answer=LOW_CONFIDENCE_RESPONSE,
                needs_escalation=True,
                disclaimer_injected=False,
            )

        # Cảnh báo khi confidence trung bình
        if confidence < 0.70:
            escalation_note = (
                "\n\n💡 **Lưu ý:** Độ tin cậy của câu trả lời này ở mức trung bình. "
                "Bạn nên xác minh thêm với chuyên gia tài chính."
            )
            answer = answer + escalation_note

        # Inject mandatory disclaimer (luôn luôn)
        final = answer.rstrip() + ADVISORY_DISCLAIMER

        return OutputGuardResult(
            passed=True,
            confidence=confidence,
            final_answer=final,
            needs_escalation=False,
            disclaimer_injected=True,
        )

    def check_knowledge(
        self,
        answer: str,
        retrieval_quality: float,
        num_docs: int,
    ) -> OutputGuardResult:
        """Knowledge output — gate lỏng hơn advisory."""
        confidence = retrieval_quality
        if num_docs == 0:
            confidence = max(0.0, confidence - 0.3)

        if confidence < self.CONFIDENCE_GATE_KNOWLEDGE:
            return OutputGuardResult(
                passed=False,
                confidence=confidence,
                final_answer=(
                    "Tôi không tìm thấy thông tin đủ chính xác để trả lời câu hỏi này. "
                    "Vui lòng thử hỏi với từ khóa cụ thể hơn."
                ),
                needs_escalation=False,
            )

        return OutputGuardResult(
            passed=True,
            confidence=confidence,
            final_answer=answer,
            needs_escalation=False,
            disclaimer_injected=False,
        )

    def check_complaint(self, answer: str) -> OutputGuardResult:
        """Complaint output — đơn giản nhất, không cần disclaimer đầu tư."""
        return OutputGuardResult(
            passed=True,
            confidence=0.85,
            final_answer=answer,
            needs_escalation=False,
            disclaimer_injected=False,
        )


# ─── CRAG — Corrective RAG self-evaluation ───────────────────────────────────

class CRAGEvaluator:
    """
    Corrective RAG: LLM tự đánh giá relevance của retrieved docs
    TRƯỚC KHI generate answer.

    Kết quả:
      CORRECT   → docs đủ liên quan, generate bình thường
      AMBIGUOUS → docs liên quan một phần, cần refine query
      INCORRECT → docs không liên quan, dùng fallback
    """

    CORRECT   = "CORRECT"
    AMBIGUOUS = "AMBIGUOUS"
    INCORRECT = "INCORRECT"

    def __init__(self, llm=None):
        self._llm = llm

    async def evaluate(self, query: str, docs: List[Any]) -> str:
        """Đánh giá relevance của docs vs query. Trả về CORRECT/AMBIGUOUS/INCORRECT."""
        if not docs:
            return self.INCORRECT

        if self._llm is None:
            # Fallback: heuristic score nếu không có LLM
            return self._heuristic_eval(query, docs)

        # Lấy sample context (tránh gửi quá nhiều token)
        sample_context = "\n---\n".join(
            d.page_content[:300] for d in docs[:3]
        )

        prompt = (
            f"Query: {query}\n\n"
            f"Retrieved context (sample):\n{sample_context}\n\n"
            "Is the retrieved context RELEVANT to answer the query?\n"
            "Reply with exactly ONE word: CORRECT, AMBIGUOUS, or INCORRECT.\n"
            "- CORRECT: context directly answers the query\n"
            "- AMBIGUOUS: context is partially related\n"
            "- INCORRECT: context is not related to the query"
        )

        try:
            from langchain_core.messages import HumanMessage
            result = await self._llm.ainvoke([HumanMessage(content=prompt)])
            label = result.content.strip().upper()
            if label in (self.CORRECT, self.AMBIGUOUS, self.INCORRECT):
                logger.info(f"CRAG eval: {label} for '{query[:50]}'")
                return label
            return self.AMBIGUOUS
        except Exception as e:
            logger.warning(f"CRAG evaluation failed: {e}")
            return self._heuristic_eval(query, docs)

    @staticmethod
    def _heuristic_eval(query: str, docs: List[Any]) -> str:
        """Heuristic: đếm query keywords xuất hiện trong docs."""
        keywords = set(re.findall(r"[a-zA-ZÀ-ỹ]{3,}", query.lower()))
        if not keywords:
            return CRAGEvaluator.AMBIGUOUS

        all_text = " ".join(d.page_content.lower() for d in docs)
        matched = sum(1 for kw in keywords if kw in all_text)
        ratio = matched / len(keywords)

        if ratio >= 0.6:
            return CRAGEvaluator.CORRECT
        if ratio >= 0.3:
            return CRAGEvaluator.AMBIGUOUS
        return CRAGEvaluator.INCORRECT
