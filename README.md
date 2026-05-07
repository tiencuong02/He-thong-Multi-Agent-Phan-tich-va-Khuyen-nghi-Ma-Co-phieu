# Multi-Agent Stock Advisor

Hệ thống phân tích cổ phiếu AI sử dụng kiến trúc **Đa tác nhân (Multi-Agent)** với LangGraph, FastAPI, MongoDB, Redis và React — tích hợp **Advanced Agentic RAG Chatbot** chuyên nghiệp cho tư vấn đầu tư chứng khoán.

## Tính năng nổi bật

### Phân tích cổ phiếu (Multi-Agent Pipeline)

- **LangGraph StateGraph**: Điều phối 3 agent tuần tự qua shared state (`StockState`), dừng tự động khi gặp lỗi.
- **Market Researcher**: Thu thập đồng thời giá lịch sử và tin tức qua `asyncio.gather`. Nguồn giá: mã VN dùng **parallel race** TCBS API vs Yahoo Finance (.VN) — ai về trước thắng; mã US dùng Yahoo Finance → Alpha Vantage fallback.
- **Financial Analyst**: Tính toán chỉ số kỹ thuật thuần thuật toán — SMA (MA5/MA20/MA50/MA100), EMA12/EMA26, RSI-14 (Wilder's Smoothed), MACD (12/26/9), Bollinger Bands (20 kỳ, 2σ), ATR-14, ADX-14 (+DI/−DI), xu hướng 5 nến, biến động khối lượng, tổng hợp sentiment.
- **Investment Advisor + TechnicalAnchor**: Khuyến nghị BUY/HOLD/SELL bằng **rule-based multi-factor scoring** (không dùng LLM) — thang điểm −10→+10 qua 8 yếu tố. Target price và stop-loss động tính từ ATR. Kết quả là **TechnicalAnchor** — nguồn sự thật duy nhất cho synthesis LLM.

### AI Chatbot & Advanced Agentic RAG

- **Guardrails 3 tầng**: Input Guard (validate, chống Prompt Injection, mask dữ liệu nhạy cảm) → Retrieval Guard (chất lượng context) → Output Guard (confidence gate, disclaimer tự động, phát hiện hallucination).
- **Intent Router**: Phân loại `ADVISORY / KNOWLEDGE / COMPLAINT / OUT_OF_SCOPE` bằng rule-based regex (fast-path, 0 LLM) + LLM fallback khi không chắc.
- **Native Tool Calling (2 vòng)**:
  - Round 1: LLM tự chọn tool phù hợp (hoặc bị bypass bởi pre-route rule-based để tiết kiệm quota).
  - Round 2: LLM synthesis tổng hợp kết quả từ tất cả tools song song.
- **8 Tools tích hợp**: `get_price_info`, `get_technical_analysis`, `get_rag_advisory`, `get_rag_knowledge`, `get_faq`, `get_market_overview`, `get_stock_news`, `get_top_buy_list`.
- **Shortcut Pipelines (0 LLM call)**: Giá cổ phiếu, so sánh giá, top mã BUY → trả về trực tiếp từ data source, không tốn Gemini quota.
- **Hybrid Search & Reranking**: Dense (MiniLM-L12-v2) + BM25 Sparse + RRF Fusion + Cross-Encoder Rerank.
- **Hierarchical Chunking (Small-to-Big)**: Child chunk (1500 chars) dùng để embed & retrieve chính xác; Parent chunk (3000 chars) đưa vào LLM để có đủ context.
- **CRAG (Corrective RAG)**: Heuristic score-based → LLM Judge chỉ khi AMBIGUOUS (tiết kiệm ~75% quota CRAG).
- **Multi-Namespace Pinecone**: 3 ngăn bảo mật độc lập: `internal-advisory`, `public-knowledge`, `faq-complaint`.
- **LLM Fallback Chain**: Gemini 2.5 Flash → Groq Llama-3.3-70b → Pre-computed Anchor (tự động khi bị rate limit/503, provider khác nhau hoàn toàn để tránh single point of failure).
- **Session Ticker Cache**: Redis lưu ngữ cảnh mã cổ phiếu xuyên suốt hội thoại.
- **Response Cache**: Redis cache câu trả lời theo MD5 hash query (TTL 2h) để tránh gọi LLM lặp. Chỉ cache khi không có conversation history (tránh trả lời sai ngữ cảnh).
- **Conversation Memory (Server-side)**: Redis list `conv:{session_id}` lưu lịch sử hội thoại phía server — tối đa 10 turns, TTL 2h. Pipeline tự load lịch sử Redis thay vì phụ thuộc client gửi lại toàn bộ history.
- **Rate Limiting**: Redis-backed, 30 req/min (stream) / 60 req/min (query) per user.
- **Streaming (SSE)**: Server-Sent Events truyền phát token realtime.

### Xác thực & Phân quyền

- **OAuth2 + JWT**: Đăng nhập/Đăng ký với access token.
- **RBAC**: Hai vai trò — `USER` và `ADMIN`.
- **User Profile**: Quản lý thông tin cá nhân, phong cách đầu tư.

### Admin Dashboard

- **Knowledge Base Manager**: Upload PDF → Hierarchical Chunking → Background embedding → Pinecone. Tự động route namespace theo ticker/loại tài liệu. Hỗ trợ reindex (chuyển ngăn), xóa document.
- **Document Suggestions API**: Cung cấp chip gợi ý tài liệu cho chatbot theo tài liệu thực đã upload.
- **Tổng quan hệ thống**: Top stocks, recommendation trends, RAG retrieval metrics.
- **Quote Management**: Tạo/sửa/xóa quote cảm hứng.
- **User Activity Analytics**: Tần suất truy cập, lịch sử hoạt động, top cổ phiếu tìm nhiều nhất.

### Frontend

- **React 18 + Vite**: Giao diện tách biệt logic (Custom Hooks) và UI (Components).
- **Biểu đồ giá**: Recharts LineChart — giá đóng cửa + MA5/MA20 overlay, 60 ngày gần nhất.
- **Lịch sử gần đây**: Hiển thị 10 mã phân tích gần nhất với khuyến nghị và xu hướng.
- **Chatbot Widget**: Streaming SSE, session context, PDF suggestion chips, conversation history.
- **Responsive Design**: Mobile-first, custom CSS + Framer Motion animations.

## Công nghệ sử dụng

| Layer | Công nghệ |
|---|---|
| **AI Orchestration** | LangGraph (StateGraph) |
| **Agent Scoring** | Rule-based multi-factor + TechnicalAnchor (không dùng LLM) |
| **LLM Synthesis** | Google Gemini 2.5 Flash (`langchain-google-genai`) |
| **LLM Fallback** | Groq Llama-3.3-70b (`langchain-groq`) → Pre-computed Anchor (last resort) |
| **Embeddings** | `paraphrase-multilingual-MiniLM-L12-v2` (384-dim, HuggingFace, CPU) |
| **Reranking** | Cross-Encoder (`ms-marco-MiniLM-L-6-v2`, fallback `mmarco-mMiniLMv2`) |
| **RAG Store** | LangChain + Pinecone (3 Namespaces) |
| **Hybrid Search** | Dense (cosine) + BM25 (`rank_bm25`) + RRF Fusion |
| **Stock Data** | TCBS API → Yahoo Finance (`yfinance`) → Alpha Vantage |
| **News** | VnNews / CafeF (tổng hợp), Alpha Vantage NEWS_SENTIMENT |
| **Backend API** | FastAPI + Uvicorn |
| **Cache** | Redis 7 (response cache, rate limit, session ticker, job state) |
| **Database** | MongoDB 6 (motor async driver) |
| **Authentication** | JWT / OAuth2 (python-jose, passlib) |
| **Frontend** | React 18, Vite, React Router v7 |
| **Charts** | Recharts (LineChart + MA overlay) |
| **Animations** | Framer Motion |
| **Container** | Docker + Docker Compose |

## Hướng dẫn cài đặt và Chạy

### 1. Chuẩn bị môi trường

Tạo file `.env` tại thư mục `backend/`:

```bash
cp backend/.env.example backend/.env
# Điền các API keys vào backend/.env
```

Các key cần thiết:
```
GEMINI_API_KEY=          # Google AI Studio
GROQ_API_KEY=            # Groq (LLM fallback, tuỳ chọn)
PINECONE_API_KEY=        # Pinecone vector store
PINECONE_INDEX_NAME=     # Tên index Pinecone (dimension=384, metric=cosine)
MONGODB_URI=             # MongoDB connection string
REDIS_URL=               # Redis connection string
```

```bash
cd backend
pip install -r requirements.txt
```

### 2. Khởi chạy

**Docker (khuyên dùng):**

```bash
docker-compose up --build
```

**Local (manual):**

```bash
# Terminal 1 — Backend API
cd backend && uvicorn app.main:app --reload

# Terminal 2 — Frontend
cd frontend && npm install && npm run dev
```

Sau khi khởi động:
- Frontend: http://localhost:3000
- Backend API docs: http://localhost:8000/docs

## Kiến trúc hệ thống

Chi tiết xem tại [architecture.md](./architecture.md).
