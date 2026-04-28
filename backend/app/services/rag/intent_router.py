"""
Intent Router — phân loại query vào đúng pipeline xử lý.

4 loại intent:
  ADVISORY   — tư vấn đầu tư, mua/bán cổ phiếu (rủi ro cao, pipeline chặt nhất)
  KNOWLEDGE  — giải đáp kiến thức CK, pháp luật, thuật ngữ (rủi ro trung bình)
  COMPLAINT  — khiếu nại, hỗ trợ tài khoản (rủi ro thấp, route sang FAQ)
  OUT_OF_SCOPE — ngoài phạm vi tài chính (từ chối lịch sự)
"""

import re
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional, List

logger = logging.getLogger(__name__)


class Intent(str, Enum):
    ADVISORY     = "ADVISORY"
    KNOWLEDGE    = "KNOWLEDGE"
    COMPLAINT    = "COMPLAINT"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"


@dataclass
class IntentResult:
    intent: Intent
    confidence: float          # 0.0 – 1.0
    reason: str                # lý do phân loại (dùng để debug)
    needs_clarification: bool  # True nếu confidence < ngưỡng → hỏi lại user


# ─── Keyword rules ────────────────────────────────────────────────────────────
# Fast-path: rule-based trước — nhanh, không tốn API call
# Slow-path: LLM classify nếu rule không quyết định được

_ADVISORY_PATTERNS: List[str] = [
    r"\b(mua|bán|có nên mua|có nên bán|nên mua|nên bán|nắm giữ|gia tăng|thoát hàng)\b",
    r"\b(tư vấn|khuyến nghị|khuyến cáo|đánh giá|nhận định)\b.*\b(mã|cổ phiếu|chứng khoán|cp|đầu tư)\b",
    r"^tư vấn đầu tư",
    r"\b(đầu tư vào|rót tiền vào|xuống tiền|vào hàng)\b",
    r"\b(giá mục tiêu|target price|stop.?loss|cắt lỗ|chốt lời|điểm vào|điểm ra)\b",
    r"\b(hold|buy|sell|tích lũy|phân phối|gom|xả)\b.*\b(mã|cổ phiếu|cp)\b",
    r"\bcó tiềm năng (tăng|giảm|sinh lời|đột phá)\b",
    r"\bphân tích (kỹ thuật|cơ bản|fundamental|technical)\b.*\b[A-Z]{2,5}\b",
    r"\bphân tích\b.{0,30}\b[A-Z]{2,5}\b",
    r"\b[A-Z]{2,5}\b.{0,30}\bphân tích\b",
    r"\b(triển vọng|tiềm năng|rủi ro|cơ hội)\b.*\b(đầu tư|cổ phiếu|thị trường)\b",
    r"\b(danh mục|portfolio|allocation)\b.*(phân bổ|điều chỉnh)\b",
    r"\bnên giữ hay bán\b",
    r"\b(tình hình|diễn biến|trạng thái)\b.*\b(cổ phiếu|mã|cp)\b",
]

_KNOWLEDGE_PATTERNS: List[str] = [
    r"\b(là gì|định nghĩa|khái niệm|giải thích|ý nghĩa|thế nào là)\b",
    r"^giải đáp kiến thức",
    r"\b(pháp luật|quy định|thông tư|nghị định|luật chứng khoán|luật doanh nghiệp)\b",
    r"\b(cách tính|công thức|phương pháp tính|tính như thế nào)\b",
    r"\b(RSI|MACD|EMA|SMA|P/E|P/B|ROE|ROA|EPS|EBITDA|CASA|NPL|NIM|CAR)\b",
    r"\b(chứng khoán phái sinh|ETF|trái phiếu|cổ tức|quyền mua|thị trường tập trung)\b",
    r"\b(cách|hướng dẫn|quy trình|thủ tục)\b.*(đặt lệnh|mở tài khoản|nộp thuế|chuyển tiền)\b",
    r"\b(báo cáo tài chính|bctc|tài chính doanh nghiệp|báo cáo thường niên|báo cáo)\b",
    r"\b(doanh thu|lợi nhuận|nợ xấu|vốn điều lệ|vốn chủ sở hữu|tài sản)\b",
    r"\b(tăng trưởng|sụt giảm|biến động|kết quả kinh doanh)\b",
    r"\b(ủy ban chứng khoán|SSC|HoSE|HNX|UPCOM)\b",
    r"\b(T\+[0-9]|lệnh|khớp lệnh|thanh toán)\b",
    r"\bhỏi về\b|\bmuốn biết\b|\bcho tôi biết\b",
]

_COMPLAINT_PATTERNS: List[str] = [
    r"\b(khiếu nại|phàn nàn|than phiền|complain)\b",
    r"^hỗ trợ tài khoản",
    r"\b(lỗi|sự cố|không thể|không hoạt động)\b.*(tài khoản|lệnh|giao dịch|đăng nhập)\b",
    r"\b(bị trừ tiền|tiền bị|tài khoản bị)\b",
    r"\b(hỗ trợ|support|liên hệ|hotline)\b",
    r"\b(không nhận được|chưa nhận|chưa thanh toán)\b",
    r"\b(sai thông tin|thông tin sai|nhầm lệnh)\b",
    r"\b(hoàn tiền|hoàn lại|refund)\b",
    r"\btài khoản (bị khóa|bị tạm khóa|không vào được)\b",
]

_GREETING_PATTERNS: List[str] = [
    r"^(xin\s*chào|chào|hello|hi|hey|helo|chao)\b",
    r"^(good\s*(morning|afternoon|evening|night))\b",
    r"^(alo|a\s*lô)\b",
    r"^(bạn\s*(ơi|có\s*thể|giúp)|cho\s*hỏi\s*chút|hỏi\s*chút|cho\s*hỏi)$",
    r"^(bạn\s*là\s*ai|bạn\s*có\s*thể\s*làm\s*gì|bạn\s*hỗ\s*trợ\s*gì|bạn\s*biết\s*gì)",
    r"^(em\s*có\s*thể\s*(giúp|hỗ\s*trợ)|anh\s*ơi|chị\s*ơi)\b",
    r"^(giới\s*thiệu|menu|help|\?+|\.+)$",
    r"^(tôi\s*cần\s*giúp|cần\s*tư\s*vấn|tư\s*vấn\s*gì|hỗ\s*trợ\s*gì)$",
    r"^(ok|okay|oke|okie|được|vâng|dạ|ừ|uhm|uh|hmm)$",
    r"^(thế\s*à|vậy\s*à|thật\s*à|ừ\s*nhỉ|ừm)$",
]

_OUT_OF_SCOPE_PATTERNS: List[str] = [
    r"\b(thời tiết|bóng đá|âm nhạc|phim|game|nấu ăn|du lịch)\b",
    r"\b(viết code|lập trình|python|javascript)\b",
    r"\b(tình yêu|hôn nhân|gia đình|sức khỏe|y tế)\b",
    r"\b(chính trị|bầu cử|đảng phái)\b",
    r"\b(crypto|bitcoin|ethereum|NFT|defi)\b(?!.*chứng khoán)",  # crypto thuần túy
    r"\b(forex|ngoại hối)\b(?!.*chứng khoán)",
]


class IntentRouter:
    """
    Rule-based fast-path + LLM slow-path cho intent classification.
    Không cần API call cho phần lớn queries (rule match > 90%).
    """

    CONFIDENCE_THRESHOLD = 0.65  # dưới ngưỡng → hỏi lại user

    def __init__(self, llm=None):
        # LLM fallback khi rule không xác định được (optional)
        self._llm = llm
        self._compiled = self._compile_patterns()

    def _compile_patterns(self):
        flags = re.IGNORECASE | re.UNICODE
        self._greeting_compiled = [re.compile(p, flags) for p in _GREETING_PATTERNS]
        return {
            Intent.ADVISORY:     [re.compile(p, flags) for p in _ADVISORY_PATTERNS],
            Intent.KNOWLEDGE:    [re.compile(p, flags) for p in _KNOWLEDGE_PATTERNS],
            Intent.COMPLAINT:    [re.compile(p, flags) for p in _COMPLAINT_PATTERNS],
            Intent.OUT_OF_SCOPE: [re.compile(p, flags) for p in _OUT_OF_SCOPE_PATTERNS],
        }

    def classify(self, query: str) -> IntentResult:
        """
        Classify query intent. Fast rule-based path — không async, không API call.
        Gọi classify_with_llm() nếu cần LLM fallback.
        """
        q = query.strip()
        if not q:
            return IntentResult(
                intent=Intent.OUT_OF_SCOPE,
                confidence=1.0,
                reason="Empty query",
                needs_clarification=False,
            )

        # Greeting fast-path — trả về capabilities menu, không cần tốn API call
        for pattern in self._greeting_compiled:
            if pattern.search(q):
                return IntentResult(
                    intent=Intent.OUT_OF_SCOPE,
                    confidence=0.95,
                    reason="Greeting detected",
                    needs_clarification=False,
                )

        scores: dict[Intent, int] = {
            Intent.ADVISORY:     0,
            Intent.KNOWLEDGE:    0,
            Intent.COMPLAINT:    0,
            Intent.OUT_OF_SCOPE: 0,
        }

        for intent, patterns in self._compiled.items():
            for pattern in patterns:
                if pattern.search(q):
                    scores[intent] += 1

        # OUT_OF_SCOPE override: nếu match thì chặn luôn
        if scores[Intent.OUT_OF_SCOPE] >= 1:
            return IntentResult(
                intent=Intent.OUT_OF_SCOPE,
                confidence=0.90,
                reason=f"Out-of-scope keywords matched ({scores[Intent.OUT_OF_SCOPE]})",
                needs_clarification=False,
            )

        best_intent = max(scores, key=lambda i: scores[i])
        best_score  = scores[best_intent]
        total       = sum(scores.values()) or 1

        # Không có pattern nào match → uncertainty
        if best_score == 0:
            return IntentResult(
                intent=Intent.KNOWLEDGE,   # default fallback
                confidence=0.40,
                reason="No pattern matched — defaulting to KNOWLEDGE",
                needs_clarification=True,
            )

        confidence = min(0.5 + (best_score / total) * 0.5, 0.95)

        # ADVISORY luôn được ưu tiên nếu có bất kỳ match nào
        # (thà false positive advisory còn hơn bỏ sót tư vấn rủi ro cao)
        if scores[Intent.ADVISORY] >= 1 and best_score >= 1:
            best_intent = Intent.ADVISORY
            confidence  = max(confidence, 0.75)

        return IntentResult(
            intent=best_intent,
            confidence=confidence,
            reason=f"Pattern scores: {dict(scores)}",
            needs_clarification=confidence < self.CONFIDENCE_THRESHOLD,
        )

    async def classify_with_llm(self, query: str) -> IntentResult:
        """
        LLM-based classification — dùng khi rule-based không tự tin.
        Chỉ gọi khi needs_clarification=True từ classify().
        """
        rule_result = self.classify(query)
        if not rule_result.needs_clarification or self._llm is None:
            return rule_result

        prompt = (
            "Classify the following user query into exactly ONE category:\n"
            "- ADVISORY: investment advice, buy/sell recommendations, portfolio decisions\n"
            "- KNOWLEDGE: definitions, explanations, how-to, regulations, financial terms\n"
            "- COMPLAINT: account issues, errors, support requests, disputes\n"
            "- OUT_OF_SCOPE: unrelated to finance/stock market\n\n"
            f"Query: {query}\n\n"
            "Reply with ONLY the category name, nothing else."
        )

        try:
            from langchain_core.messages import HumanMessage
            result = await self._llm.ainvoke([HumanMessage(content=prompt)])
            label = result.content.strip().upper()
            intent_map = {
                "ADVISORY":     Intent.ADVISORY,
                "KNOWLEDGE":    Intent.KNOWLEDGE,
                "COMPLAINT":    Intent.COMPLAINT,
                "OUT_OF_SCOPE": Intent.OUT_OF_SCOPE,
            }
            llm_intent = intent_map.get(label, rule_result.intent)
            logger.info(f"IntentRouter LLM: '{label}' for query: '{query[:60]}'")
            return IntentResult(
                intent=llm_intent,
                confidence=0.82,
                reason=f"LLM classified as {label}",
                needs_clarification=False,
            )
        except Exception as e:
            logger.warning(f"LLM intent classification failed: {e}")
            return rule_result

    @staticmethod
    def get_clarification_message(query: str) -> str:
        return (
            "Xin lỗi, tôi chưa hiểu rõ câu hỏi của bạn. Bạn muốn:\n\n"
            "1. **Tư vấn đầu tư** — mua/bán/giữ cổ phiếu cụ thể?\n"
            "2. **Giải đáp kiến thức** — thuật ngữ, quy định, cách tính chỉ số?\n"
            "3. **Hỗ trợ tài khoản** — vấn đề giao dịch, khiếu nại?\n\n"
            "Vui lòng chọn hoặc nói rõ hơn để tôi hỗ trợ chính xác."
        )
