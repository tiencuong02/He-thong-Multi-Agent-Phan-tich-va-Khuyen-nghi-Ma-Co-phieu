"""
ChatTools — Native Tool Calling cho RAG Pipeline.

LLM nhận danh sách tools, tự suy luận gọi 1 hoặc nhiều tools cùng lúc.
Kết quả các tools được thu thập song song rồi đưa vào LLM synthesis.

Tools:
  get_price_info          — giá cổ phiếu hiện tại
  get_technical_analysis  — chỉ báo kỹ thuật + TechnicalAnchor
  get_rag_advisory        — RAG báo cáo tài chính (advisory namespace)
  get_rag_knowledge       — RAG kiến thức chứng khoán
  get_faq                 — FAQ hỗ trợ khách hàng
  get_market_overview     — tổng quan thị trường VN
  get_stock_news          — tin tức cổ phiếu
  get_top_buy_list        — danh sách mã được khuyến nghị BUY

Flow:
  1. LLM (Gemini) nhận query + tool schemas → quyết định tool_calls
  2. Execute tất cả tool_calls song song (asyncio.gather)
  3. Tập hợp kết quả + TechnicalAnchor → đưa vào synthesis LLM
  4. Synthesis LLM bắt buộc dùng Technical Anchor nếu có
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple

from langchain_core.messages import ToolMessage

logger = logging.getLogger(__name__)

# ─── Tool JSON Schemas (gửi cho Gemini bind_tools) ───────────────────────────

TOOL_DEFINITIONS = [
    {
        "name": "get_price_info",
        "description": (
            "Lấy giá cổ phiếu hiện tại (open, high, low, close, volume). "
            "Dùng khi hỏi về giá, biến động giá, so sánh giá hôm nay."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Mã cổ phiếu (VD: FPT, VNM, AAPL, TSLA)",
                }
            },
            "required": ["ticker"],
        },
    },
    {
        "name": "get_technical_analysis",
        "description": (
            "Tính chỉ báo kỹ thuật (RSI, MACD, Bollinger, SMA) và đưa ra khuyến nghị "
            "BUY/SELL/HOLD xác định. Dùng khi cần phân tích kỹ thuật hoặc tư vấn đầu tư."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Mã cổ phiếu",
                }
            },
            "required": ["ticker"],
        },
    },
    {
        "name": "get_rag_advisory",
        "description": (
            "Tìm kiếm thông tin từ báo cáo tài chính, phân tích cơ bản (doanh thu, lợi nhuận, "
            "ROE, EPS, chiến lược kinh doanh). Dùng khi cần phân tích cơ bản hoặc hỏi về "
            "tình hình kinh doanh của công ty."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Mã cổ phiếu cần tra cứu",
                },
                "query": {
                    "type": "string",
                    "description": "Câu hỏi cụ thể để tìm kiếm trong tài liệu",
                },
            },
            "required": ["ticker", "query"],
        },
    },
    {
        "name": "get_rag_knowledge",
        "description": (
            "Tra cứu kiến thức chứng khoán: định nghĩa thuật ngữ, quy định pháp luật, "
            "cách tính chỉ số tài chính, hướng dẫn giao dịch."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Câu hỏi kiến thức cần tra cứu",
                }
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_faq",
        "description": (
            "Tra cứu FAQ hỗ trợ khách hàng: vấn đề tài khoản, lỗi giao dịch, "
            "khiếu nại, hướng dẫn sử dụng."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Vấn đề cần hỗ trợ",
                }
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_market_overview",
        "description": (
            "Lấy tổng quan thị trường chứng khoán Việt Nam hôm nay "
            "(VN-Index, VN30, top tăng/giảm, breadth)."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_stock_news",
        "description": (
            "Lấy tin tức mới nhất về một mã cổ phiếu hoặc thị trường chung."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Mã cổ phiếu (để trống nếu hỏi tin thị trường chung)",
                }
            },
            "required": [],
        },
    },
    {
        "name": "get_top_buy_list",
        "description": (
            "Lấy danh sách mã cổ phiếu đang được khuyến nghị MUA từ hệ thống phân tích."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]


# ─── Tool Executor ────────────────────────────────────────────────────────────

class ToolExecutor:
    """
    Thực thi các tool calls mà LLM đã chọn.
    Mỗi tool trả về (result_text, anchor) — anchor có thể None.
    """

    def __init__(self, vector_store, rag_pipeline):
        self._vs  = vector_store
        self._rag = rag_pipeline

    async def execute_all(
        self,
        tool_calls: List[Dict[str, Any]],
    ) -> List[Tuple[str, str, str, Any, Any]]:
        """
        Thực thi tất cả tool_calls song song.
        Returns: list of (tool_call_id, tool_name, result_text, anchor_or_None, sources_or_None)
        """
        tasks = [self._execute_one(tc) for tc in tool_calls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        out = []
        for tc, result in zip(tool_calls, results):
            tc_id   = tc.get("id", tc.get("name", "unknown"))
            tc_name = tc.get("name", "unknown")
            if isinstance(result, Exception):
                logger.error(f"Tool {tc_name} failed: {result}")
                out.append((tc_id, tc_name, f"[Lỗi khi gọi {tc_name}: {result}]", None, None))
            else:
                text, anchor, sources = result
                out.append((tc_id, tc_name, text, anchor, sources))
        return out

    async def _execute_one(self, tc: Dict[str, Any]) -> Tuple[str, Any, Any]:
        name = tc.get("name", "")
        args = tc.get("args", {})

        dispatch = {
            "get_price_info":         self._price_info,
            "get_technical_analysis": self._technical_analysis,
            "get_rag_advisory":       self._rag_advisory,
            "get_rag_knowledge":      self._rag_knowledge,
            "get_faq":                self._faq,
            "get_market_overview":    self._market_overview,
            "get_stock_news":         self._stock_news,
            "get_top_buy_list":       self._top_buy_list,
        }
        fn = dispatch.get(name)
        if fn is None:
            return f"Tool '{name}' không tồn tại.", None, None
        return await fn(args)

    # ── Individual tool implementations ─────────────────────────────────────
    # Tất cả trả về (content: str, anchor: Any|None, sources: List|None)

    async def _price_info(self, args: Dict) -> Tuple[str, None, None]:
        ticker = args.get("ticker", "").upper()
        if not ticker:
            return "Cần cung cấp mã cổ phiếu.", None, None
        try:
            result = await self._rag._fetch_price_response(ticker)
            return result.get("answer", "Không lấy được dữ liệu giá."), None, None
        except Exception as e:
            return f"Lỗi lấy giá {ticker}: {e}", None, None

    async def _technical_analysis(self, args: Dict) -> Tuple[str, Any, None]:
        """Returns (context_text, TechnicalAnchor, None)."""
        ticker = args.get("ticker", "").upper()
        if not ticker:
            return "Cần cung cấp mã cổ phiếu.", None, None
        try:
            from app.services.alpha_vantage import AlphaVantageService
            from app.services.technical_analysis import TechnicalAnalysisService
            from app.services.investment_rule_engine import InvestmentRuleEngine

            data   = await AlphaVantageService.fetch_stock_data(ticker)
            prices = data.get("prices", [])
            if not prices or len(prices) < 30:
                return f"Không đủ dữ liệu lịch sử để phân tích kỹ thuật {ticker}.", None, None

            ta = TechnicalAnalysisService.compute(prices)
            if ta is None:
                return f"Không thể tính chỉ báo kỹ thuật cho {ticker}.", None, None

            anchor  = InvestmentRuleEngine.compute_anchor(ticker, ta)
            context = (
                TechnicalAnalysisService.format_for_llm(ticker, ta)
                + "\n\n"
                + InvestmentRuleEngine.format_for_llm(anchor)
            )
            return context, anchor, None
        except Exception as e:
            logger.error(f"_technical_analysis {ticker}: {e}")
            return f"Lỗi phân tích kỹ thuật {ticker}: {e}", None, None

    async def _rag_advisory(self, args: Dict) -> Tuple[str, None, Any]:
        """Returns (context_text, None, actual_pdf_sources)."""
        ticker      = args.get("ticker", "").upper()
        query       = args.get("query", "")
        filter_meta = {"ticker": ticker} if ticker else {}
        try:
            rewrite_q = await self._rag._rewrite_query(query or ticker)
            docs = await asyncio.to_thread(
                self._vs.search_advisory, rewrite_q, 8, filter_meta
            )
            rg = self._rag._retrieval_guard.check_advisory(docs)
            if not rg.passed:
                return f"Không tìm thấy tài liệu phân tích cho {ticker or 'chủ đề này'}.", None, None

            context     = self._rag._format_context(rg.filtered_docs)
            # Lấy sources thật (tên file PDF + số trang) để surface lên frontend
            pdf_sources = self._rag._extract_sources(rg.filtered_docs)
            src_str     = ", ".join(
                f"{s['source']} tr.{s['page']}" for s in pdf_sources[:3]
            )
            return f"[Nguồn tài liệu: {src_str}]\n\n{context}", None, pdf_sources
        except Exception as e:
            logger.error(f"_rag_advisory {ticker}: {e}")
            return f"Lỗi truy vấn tài liệu: {e}", None, None

    async def _rag_knowledge(self, args: Dict) -> Tuple[str, None, Any]:
        query = args.get("query", "")
        try:
            docs = await asyncio.to_thread(self._vs.search_knowledge, query, 6, {})
            rg   = self._rag._retrieval_guard.check_knowledge(docs)
            if not rg.filtered_docs:
                return "Không tìm thấy tài liệu liên quan.", None, None
            pdf_sources = self._rag._extract_sources(rg.filtered_docs)
            return self._rag._format_context(rg.filtered_docs), None, pdf_sources
        except Exception as e:
            logger.error(f"_rag_knowledge: {e}")
            return f"Lỗi tra cứu kiến thức: {e}", None, None

    async def _faq(self, args: Dict) -> Tuple[str, None, None]:
        query = args.get("query", "")
        try:
            docs = await asyncio.to_thread(self._vs.search_faq, query, 3)
            rg   = self._rag._retrieval_guard.check_complaint(docs)
            if not rg.filtered_docs:
                return "Không tìm thấy câu trả lời trong FAQ.", None, None
            return self._rag._format_context(rg.filtered_docs), None, None
        except Exception as e:
            return f"Lỗi tra cứu FAQ: {e}", None, None

    async def _market_overview(self, args: Dict) -> Tuple[str, None, None]:
        try:
            from app.services.market_overview import MarketOverviewService
            overview = await asyncio.wait_for(
                MarketOverviewService.get_overview(), timeout=12.0
            )
            context = await MarketOverviewService.format_for_llm(overview)
            return context, None, None
        except Exception as e:
            return f"Lỗi lấy dữ liệu thị trường: {e}", None, None

    async def _stock_news(self, args: Dict) -> Tuple[str, None, None]:
        ticker = (args.get("ticker") or "").upper() or None
        try:
            from app.services.vn_news import VnNewsService
            news = await asyncio.wait_for(
                VnNewsService.fetch_news(ticker, max_items=8), timeout=10.0
            )
            if not news:
                return "Không tìm thấy tin tức.", None, None
            return VnNewsService.format_for_llm(ticker, news), None, None
        except Exception as e:
            return f"Lỗi lấy tin tức: {e}", None, None

    async def _top_buy_list(self, args: Dict) -> Tuple[str, None, None]:
        try:
            from app.db.mongodb import get_db
            from app.repositories.report_repository import ReportRepository
            db = get_db()
            if db is None:
                return "Không kết nối được database.", None, None
            repo    = ReportRepository(db)
            reports = await repo.get_recent_reports(limit=50)
            latest: dict = {}
            for r in reports:
                if r.ticker not in latest:
                    latest[r.ticker] = r
            buys = [
                r for r in latest.values()
                if r.recommendation and r.recommendation.upper() in ("BUY", "STRONG BUY")
            ]
            if not buys:
                return "Hiện chưa có mã nào đạt tín hiệu MUA từ hệ thống.", None, None
            lines = ["Danh sách mã được khuyến nghị MUA:"]
            for r in buys[:10]:
                lines.append(f"- {r.ticker}: {r.recommendation}")
            return "\n".join(lines), None, None
        except Exception as e:
            return f"Lỗi lấy danh sách mã BUY: {e}", None, None


# ─── Build ToolMessages for LLM synthesis ────────────────────────────────────

def build_tool_messages(
    results: List[Tuple[str, str, str, Any, Any]],
) -> List[ToolMessage]:
    """Chuyển tool results thành ToolMessage để gửi lại cho LLM synthesis."""
    msgs = []
    for tc_id, tc_name, text, _anchor, _sources in results:
        msgs.append(ToolMessage(content=text, tool_call_id=tc_id, name=tc_name))
    return msgs


def extract_anchors(
    results: List[Tuple[str, str, str, Any, Any]],
) -> List[Any]:
    """Lấy tất cả TechnicalAnchor từ tool results."""
    return [anchor for _, _, _, anchor, _ in results if anchor is not None]


def extract_rag_sources(
    results: List[Tuple[str, str, str, Any, Any]],
) -> List[dict]:
    """Lấy actual PDF sources từ get_rag_advisory results."""
    sources = []
    for _, _, _, _, extra_sources in results:
        if extra_sources:
            sources.extend(extra_sources)
    return sources
