"""
LLMProvider — Multi-provider LLM với cross-provider fallback.

Thứ tự ưu tiên:
  1. Gemini 2.5 Flash  (primary)
  2. Groq Llama-3.3-70b (fallback khi Gemini rate-limit / sập)
  3. Pre-computed Anchor (last resort — không cần LLM)

Khác biệt với rag_pipeline cũ:
  - Cũ: Gemini Flash → Gemini Flash-Lite (cùng Google infra)
  - Mới: Gemini → Groq (provider khác hoàn toàn) → Anchor text
  → Nếu Google bị sập, Groq vẫn chạy được
"""

import asyncio
import logging
from typing import AsyncGenerator, List, Optional, Tuple, Any

logger = logging.getLogger(__name__)

# Errors đáng retry (rate limit / overload) — không retry lỗi auth/not-found
_RETRYABLE = ("503", "429", "quota", "resource_exhausted", "unavailable",
              "overloaded", "rate limit", "too many", "rate_limit")


def _is_retryable(err: str) -> bool:
    e = err.lower()
    if any(x in err for x in ("404", "401")):
        return False
    return any(x in e for x in _RETRYABLE)


class LLMProvider:
    """
    Wrapper thống nhất cho Gemini + Groq.
    Inject vào RAGPipelineService thay thế self.llm trực tiếp.
    """

    def __init__(self, gemini_llm=None, groq_api_key: str = ""):
        self._gemini: Optional[Any] = gemini_llm
        self._groq:   Optional[Any] = None

        if groq_api_key:
            try:
                from langchain_groq import ChatGroq
                self._groq = ChatGroq(
                    model="llama-3.3-70b-versatile",
                    api_key=groq_api_key,
                    temperature=0.1,
                    max_tokens=4096,
                )
                logger.info("LLMProvider: Groq Llama-3.3-70b initialized.")
            except ImportError:
                logger.warning(
                    "langchain-groq not installed. "
                    "Run: pip install langchain-groq"
                )
            except Exception as e:
                logger.warning(f"LLMProvider: Groq init failed: {e}")

    @property
    def primary(self):
        """Trả về Gemini LLM (dùng cho tool calling — chỉ Gemini hỗ trợ)."""
        return self._gemini

    def _providers(self) -> List[Tuple[str, Any]]:
        result = []
        if self._gemini:
            result.append(("Gemini", self._gemini))
        if self._groq:
            result.append(("Groq",   self._groq))
        return result

    # ─── Invoke (non-streaming) ───────────────────────────────────────────────

    async def invoke(
        self,
        messages: list,
        anchor_text: str = "",
        timeout: float = 30.0,
    ) -> str:
        """
        Gọi LLM theo thứ tự ưu tiên.
        Nếu tất cả fail → trả anchor_text hoặc thông báo lỗi.
        """
        for name, llm in self._providers():
            try:
                result = await asyncio.wait_for(
                    llm.ainvoke(messages), timeout=timeout
                )
                return result.content if hasattr(result, "content") else str(result)
            except Exception as e:
                logger.warning(f"LLMProvider [{name}] invoke failed: {e}")
                if not _is_retryable(str(e)):
                    break   # lỗi auth/not-found → không thử provider tiếp

        # Anchor fallback
        if anchor_text:
            logger.warning("LLMProvider: all providers failed — using anchor fallback.")
            return f"⚠️ AI tạm thời không khả dụng.\n\n{anchor_text}"
        return "⚠️ Hệ thống AI tạm thời không khả dụng. Vui lòng thử lại sau."

    # ─── Stream ───────────────────────────────────────────────────────────────

    async def stream(
        self,
        messages: list,
        anchor_text: str = "",
        timeout: float = 75.0,
    ) -> AsyncGenerator[str, None]:
        """
        Stream theo thứ tự ưu tiên.
        Nếu Gemini fail giữa chừng → restart từ Groq (chunk đã gửi không thu hồi được,
        nhưng tốt hơn là không có gì).
        """
        for name, llm in self._providers():
            try:
                async for token in self._stream_single(llm, messages, timeout):
                    yield token
                return
            except Exception as e:
                logger.warning(f"LLMProvider [{name}] stream failed: {e}")
                if not _is_retryable(str(e)):
                    break

        # Anchor fallback
        if anchor_text:
            yield (
                "\n\n⚠️ AI tạm thời không khả dụng. "
                "Dưới đây là kết quả phân tích kỹ thuật:\n\n"
                + anchor_text
            )
        else:
            yield "⚠️ Hệ thống AI tạm thời không khả dụng. Vui lòng thử lại sau."

    @staticmethod
    async def _stream_single(
        llm, messages: list, timeout: float
    ) -> AsyncGenerator[str, None]:
        """Stream từ 1 provider với timeout guard."""
        queue: asyncio.Queue = asyncio.Queue()

        async def _producer():
            try:
                async for chunk in llm.astream(messages):
                    text = chunk.content if hasattr(chunk, "content") else str(chunk)
                    if text:
                        await queue.put(text)
            except Exception as e:
                await queue.put(Exception(str(e)))
            finally:
                await queue.put(None)

        task = asyncio.create_task(_producer())
        deadline = asyncio.get_event_loop().time() + timeout
        per_token_timeout = 50.0
        first_token = True

        try:
            while True:
                remaining = deadline - asyncio.get_event_loop().time()
                if remaining <= 0:
                    task.cancel()
                    yield "\n\n⚠️ Phản hồi bị ngắt do quá thời gian."
                    return
                try:
                    item = await asyncio.wait_for(
                        queue.get(), timeout=min(remaining, per_token_timeout)
                    )
                except asyncio.TimeoutError:
                    task.cancel()
                    yield "\n\n⚠️ Phản hồi bị ngắt do quá thời gian."
                    return

                if item is None:
                    return
                if isinstance(item, Exception):
                    raise item
                if first_token:
                    first_token = False
                    per_token_timeout = 10.0
                yield item
        finally:
            if not task.done():
                task.cancel()
