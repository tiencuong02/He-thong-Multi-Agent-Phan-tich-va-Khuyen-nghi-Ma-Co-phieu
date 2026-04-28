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

OUT_OF_SCOPE_RESPONSE = """Dạ, em có thể hỗ trợ Anh/Chị về các lĩnh vực chính sau ạ:

📊 **Thông tin thị trường & cổ phiếu:**
- Cập nhật xu hướng thị trường chứng khoán
- Thông tin các mã cổ phiếu (giá, khối lượng, biến động)
- Phân tích cơ bản & phân tích kỹ thuật
- Tin tức doanh nghiệp, ngành nghề

📈 **Tư vấn đầu tư:**
- Gợi ý danh mục cổ phiếu theo mục tiêu (ngắn hạn, dài hạn)
- Chiến lược đầu tư (lướt sóng, tích sản, giá trị…)
- Quản lý rủi ro & phân bổ vốn
- Theo dõi và tối ưu danh mục

🏢 **Dành cho nhà đầu tư:**
- Hướng dẫn mở tài khoản chứng khoán
- Cách đặt lệnh mua/bán cổ phiếu
- Sử dụng nền tảng giao dịch (app/web)
- Thông tin về phí giao dịch, thuế

💡 **Hỗ trợ & giải đáp:**
- Giải thích thuật ngữ chứng khoán
- Phân tích báo cáo tài chính cơ bản
- Nhận định thị trường theo thời điểm
- Giải đáp các thắc mắc liên quan đến đầu tư

🎯 **Cá nhân hóa tư vấn:**
- Đánh giá khẩu vị rủi ro của Anh/Chị
- Đề xuất chiến lược phù hợp
- Kết nối với chuyên gia (nếu cần)

Anh/Chị cần hỗ trợ về vấn đề nào ạ? 😊"""

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

    MAX_QUERY_LENGTH = 5000  # nới lỏng theo yêu cầu
    MIN_QUERY_LENGTH = 1

    # Prompt injection patterns — English + Vietnamese
    _INJECTION_PATTERNS = [
        # English
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
        # Vietnamese
        r"b[oỏ]\s*qua\s*(h[uướ][oớ]ng\s*d[aẫẩ]n|c[aá]c\s*quy\s*t[aắ]c|l[eệ]nh\s*tr[eướ][cớ])",
        r"qu[eê]n\s*(vai\s*tr[oò]|h[uướ][oớ]ng\s*d[aẫẩ]n|nhi[eệ]m\s*v[uụ]|quy\s*t[aắ]c)",
        r"[dđ][oó]ng\s*vai(\s+l[aà]|\s+nh[uư]|\s+m[oộ]t\s*)",
        r"gi[aả]\s*v[oờ]\s*(b[aạ]n\s*l[aà]|nh[uư]\s*l[aà])",
        r"th[aay]\s*[dđ][oổ]i\s*(vai\s*tr[oò]|nhi[eệ]m\s*v[uụ]|h[aà]nh\s*vi)",
        r"ti[eếề]t\s*l[oộ]\s*(system\s*prompt|h[uướ][oớ]ng\s*d[aẫẩ]n\s*h[eệ]\s*th[oố]ng)",
        r"ch[eế]\s*[dđ][oộ]\s*(kh[aá]c|m[oớ]i|[aẩ]n\s*)",
        r"b[aạ]n\s+th[uự]c\s+ra\s+l[aà]",
        r"(nhi[eệ]m\s*v[uụ]|vai\s*tr[oò])\s*th[uự]c\s*(s[uự]|t[eế])",
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

    # Advisory: 1 doc đã đủ — 2 là lý tưởng nhưng không thực tế với PDF nhỏ
    # Chất lượng được đảm bảo bởi CRAG evaluation và similarity threshold
    MIN_DOCS_ADVISORY  = 1
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

        # Quality score dựa trên nội dung tài chính thực sự, không chỉ độ dài
        financial_docs = sum(
            1 for d in valid_docs
            if d.metadata.get("has_numbers") or d.metadata.get("has_table")
        )
        unique_sources = len({d.metadata.get("source", "") for d in valid_docs})
        avg_len = sum(len(d.page_content) for d in valid_docs) / len(valid_docs)

        financial_ratio = financial_docs / len(valid_docs)          # 0-1
        source_diversity = min(unique_sources / 2, 1.0)             # 2+ sources = full score
        content_score = min(avg_len / 1500, 1.0)                    # 1500 chars = full score

        quality = (
            0.50 * financial_ratio    # nội dung có số liệu tài chính — quan trọng nhất
            + 0.30 * source_diversity  # đa dạng nguồn
            + 0.20 * content_score    # độ dài đủ context
        )
        quality = max(0.30, min(quality, 1.0))  # floor 0.30 nếu docs tồn tại

        return RetrievalGuardResult(
            passed=True,
            min_docs_met=True,
            quality_score=round(quality, 3),
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

    # Patterns cho thấy LLM đang bịa số liệu — chỉ khi tự nhận đang ước tính
    _FABRICATION_SIGNALS = [
        r"tôi\s+ước\s+(tính|lượng|đoán)",                          # tự nhận đang ước đoán
        r"theo\s+(cảm\s*giác|suy\s*luận|phán\s*đoán)\s*của\s*tôi",
        r"(có\s*thể\s*sẽ|chắc\s*là)\s*(tăng|giảm)\s+\d+\s*%(?!\s*theo\s*tài\s*liệu)",
        r"ước\s*tính\s+khoảng\s+\d+.*%\s*(?!trong|theo|theo\s*báo\s*cáo)",
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
        """Complaint output — tính confidence từ tín hiệu chất lượng câu trả lời."""
        length_score = min(len(answer) / 200, 1.0)
        has_action = bool(re.search(
            r"(hotline|liên\s*hệ|email|bước\s*\d|hướng\s*dẫn|gọi\s*đến|truy\s*cập)",
            answer, re.IGNORECASE,
        ))
        too_short = len(answer.strip()) < 30

        if too_short:
            return OutputGuardResult(
                passed=False,
                confidence=0.2,
                final_answer="Xin lỗi, tôi chưa tìm thấy hướng dẫn phù hợp. Vui lòng liên hệ hotline để được hỗ trợ trực tiếp.",
                needs_escalation=True,
            )

        confidence = round(0.55 + 0.25 * length_score + 0.20 * int(has_action), 2)
        confidence = min(confidence, 0.92)

        return OutputGuardResult(
            passed=True,
            confidence=confidence,
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
        """
        3-stage evaluation:
          1. Score-based heuristic (không tốn API call)
          2. Nếu AMBIGUOUS → LLM judge để phán quyết chính xác hơn
          3. Fallback về AMBIGUOUS nếu LLM lỗi/timeout
        """
        if not docs:
            return self.INCORRECT

        result = self._score_based_eval(query, docs)

        # LLM chỉ gọi khi vùng xám — CORRECT/INCORRECT không cần xác nhận
        if result == self.AMBIGUOUS and self._llm is not None:
            llm_result = await self._llm_judge(query, docs)
            logger.info(f"CRAG AMBIGUOUS → LLM override: {llm_result} | '{query[:50]}'")
            return llm_result

        logger.info(f"CRAG heuristic: {result} | '{query[:50]}'")
        return result

    async def _llm_judge(self, query: str, docs: List[Any]) -> str:
        """
        LLM phán quyết khi score nằm vùng xám 0.58-0.72.
        Dùng Gemini Flash (model chính) với timeout 8s — không ảnh hưởng nhiều đến latency.
        Sample: top 3 docs, mỗi doc tối đa 250 chars.
        Cost: ~$0.0002/call × 25% queries = rất rẻ.
        """
        import asyncio
        from langchain_core.messages import HumanMessage

        snippets = "\n---\n".join(
            d.page_content[:250].strip() for d in docs[:3]
        )
        prompt = (
            "Đánh giá các đoạn tài liệu sau có đủ thông tin để trả lời câu hỏi không.\n\n"
            f"Câu hỏi: {query}\n\n"
            f"Tài liệu:\n{snippets}\n\n"
            "Trả lời đúng 1 trong 3 từ sau (không giải thích thêm):\n"
            "CORRECT — tài liệu có đủ thông tin liên quan trực tiếp\n"
            "AMBIGUOUS — tài liệu liên quan một phần, không đủ để trả lời hoàn chỉnh\n"
            "INCORRECT — tài liệu không liên quan đến câu hỏi"
        )
        try:
            result = await asyncio.wait_for(
                self._llm.ainvoke([HumanMessage(content=prompt)]),
                timeout=8.0,
            )
            label = result.content.strip().upper().split()[0]  # lấy từ đầu tiên
            if label in (self.CORRECT, self.AMBIGUOUS, self.INCORRECT):
                return label
            logger.warning(f"CRAG LLM returned unexpected label: '{label}'")
        except asyncio.TimeoutError:
            logger.warning("CRAG LLM judge timed out — keeping AMBIGUOUS")
        except Exception as e:
            logger.warning(f"CRAG LLM judge failed: {e} — keeping AMBIGUOUS")

        return self.AMBIGUOUS  # fail-safe: cautious về advisory

    @staticmethod
    def _score_based_eval(query: str, docs: List[Any]) -> str:
        """
        Ưu tiên similarity scores từ vector retrieval (chính xác hơn keyword counting).
        Fallback về keyword overlap nếu scores không có.
        """
        # Lấy similarity scores từ metadata (VectorStoreService đã attach)
        scores = [
            float(d.metadata.get("_similarity_score", 0.0))
            for d in docs
            if d.metadata.get("_similarity_score") is not None
        ]

        if scores:
            mean_score = sum(scores) / len(scores)
            max_score  = max(scores)
            # Dùng weighted: mean * 0.6 + max * 0.4 để reward docs rất relevant
            combined = mean_score * 0.6 + max_score * 0.4

            if combined >= 0.72:
                return CRAGEvaluator.CORRECT
            if combined >= 0.58:
                return CRAGEvaluator.AMBIGUOUS
            return CRAGEvaluator.INCORRECT

        # Fallback: keyword overlap khi không có scores
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
