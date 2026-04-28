"""
TickerContextCache — Redis-backed ticker context per session.

Giải quyết vấn đề: "Vậy chốt lời bao nhiêu?" (câu thiếu chủ ngữ)
Cache nhớ mã cổ phiếu đang bàn trong 10 phút / tự renew mỗi lần dùng.

Key format : ticker_ctx:{session_id}
TTL        : 600 giây (10 phút)
Fallback   : nếu Redis không có → None (caller tự extract từ query)
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

_TTL = 600       # 10 phút
_PREFIX = "ticker_ctx:"


class TickerContextCache:

    def __init__(self, redis_client=None):
        self._redis = redis_client

    # ─── Write ────────────────────────────────────────────────────────────────

    async def set_ticker(self, session_id: str, ticker: str) -> None:
        """Lưu ticker cho session, reset TTL về 10 phút."""
        if not self._redis or not session_id or not ticker:
            return
        try:
            await self._redis.setex(_PREFIX + session_id, _TTL, ticker.upper())
            logger.debug(f"TickerCache SET {session_id} → {ticker.upper()}")
        except Exception as e:
            logger.warning(f"TickerCache SET failed: {e}")

    # ─── Read ─────────────────────────────────────────────────────────────────

    async def get_ticker(self, session_id: str) -> Optional[str]:
        """Trả về ticker đang cache, đồng thời renew TTL."""
        if not self._redis or not session_id:
            return None
        try:
            key   = _PREFIX + session_id
            value = await self._redis.get(key)
            if value:
                # Renew TTL mỗi lần đọc — giữ alive khi conversation đang active
                await self._redis.expire(key, _TTL)
                return value.upper()
            return None
        except Exception as e:
            logger.warning(f"TickerCache GET failed: {e}")
            return None

    # ─── Delete ───────────────────────────────────────────────────────────────

    async def clear(self, session_id: str) -> None:
        """Xoá cache khi conversation kết thúc hoặc chủ đề thay đổi rõ ràng."""
        if not self._redis or not session_id:
            return
        try:
            await self._redis.delete(_PREFIX + session_id)
            logger.debug(f"TickerCache CLEAR {session_id}")
        except Exception as e:
            logger.warning(f"TickerCache CLEAR failed: {e}")

    # ─── Resolve (main helper) ────────────────────────────────────────────────

    async def resolve_ticker(
        self,
        session_id: str,
        extracted_ticker: Optional[str],
    ) -> Optional[str]:
        """
        Chiến lược resolve ticker:
        1. Nếu query có ticker mới → dùng và cập nhật cache
        2. Nếu query không có ticker → lấy từ cache (câu thiếu chủ ngữ)
        3. Nếu cả hai đều None → trả None

        Gọi sau bước _extract_ticker().
        """
        if extracted_ticker:
            # Ticker mới trong query → cập nhật cache
            await self.set_ticker(session_id, extracted_ticker)
            return extracted_ticker

        # Câu thiếu chủ ngữ → fallback về cache
        cached = await self.get_ticker(session_id)
        if cached:
            logger.info(f"TickerCache HIT {session_id} → {cached} (context carry-over)")
        return cached
