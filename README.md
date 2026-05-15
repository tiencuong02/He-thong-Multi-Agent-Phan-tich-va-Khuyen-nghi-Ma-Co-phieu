# Multi-Agent Stock Analysis & Advisory Platform

> Hệ thống phân tích cổ phiếu AI sử dụng kiến trúc **Đa tác nhân (Multi-Agent)** với LangGraph, kết hợp **Advanced Agentic RAG Chatbot** chuyên nghiệp cho tư vấn đầu tư chứng khoán Việt Nam và quốc tế.

---

## Mục lục

- [Tổng quan](#tổng-quan)
- [Kiến trúc hệ thống](#kiến-trúc-hệ-thống)
- [Multi-Agent Pipeline — Cơ chế chi tiết](#multi-agent-pipeline--cơ-chế-chi-tiết)
- [RAG Chatbot — Cơ chế chi tiết](#rag-chatbot--cơ-chế-chi-tiết)
- [Công nghệ sử dụng](#công-nghệ-sử-dụng)
- [Cài đặt và chạy](#cài-đặt-và-chạy)
- [Cấu hình môi trường](#cấu-hình-môi-trường)
- [API Reference](#api-reference)
- [Cấu trúc thư mục](#cấu-trúc-thư-mục)
- [Hướng dẫn phát triển](#hướng-dẫn-phát-triển)
- [Troubleshooting](#troubleshooting)

---

## Tổng quan

Platform cung cấp hai luồng AI chính chạy song song:

**1. Multi-Agent Pipeline** — Nhập mã cổ phiếu → 3 agent LangGraph xử lý tuần tự → trả về báo cáo kỹ thuật + khuyến nghị BUY/HOLD/SELL kèm giải thích. Phân tích chạy bất đồng bộ qua Kafka, kết quả stream progress realtime về frontend.

**2. Agentic RAG Chatbot** — Hỏi đáp tự do về cổ phiếu, thị trường, tài liệu nội bộ. Streaming SSE realtime, 8 công cụ tích hợp, 3 tầng guardrail. Thiết kế tối thiểu hoá chi phí LLM: shortcut 0-call cho câu hỏi đơn giản, CRAG heuristic giảm ~75% LLM judge calls, TechnicalAnchor rule-based không cần LLM.

---

## Kiến trúc hệ thống

```
┌─────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (React 18)                         │
│  Dashboard │ TechnicalChart │ ChatBotWidget (SSE) │ AdminDashboard  │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ HTTP / SSE
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      BACKEND API (FastAPI)                          │
│                                                                     │
│  /auth  │  /stock  │  /rag  │  /quotes                             │
│                                                                     │
│  Middleware: CORS · Correlation ID · Prometheus metrics             │
└───────────┬──────────────────────┬──────────────────────────────────┘
            │                      │
     Kafka topic              RAG Pipeline
  stock_analysis_tasks        (in-process)
            │                      │
            ▼                      ▼
┌───────────────────┐   ┌──────────────────────┐
│   WORKER (Kafka   │   │   Pinecone           │
│   Consumer)       │   │   3 Namespaces       │
│   LangGraph       │   │   (Dense + BM25)     │
│   Multi-Agent     │   └──────────────────────┘
└───────────────────┘
            │
            ▼
┌───────────────────────────────────────────┐
│  Infrastructure                           │
│  MongoDB 6  │  Redis 7  │  Kafka          │
└───────────────────────────────────────────┘
```

### Docker Compose — 7 services

| Service     | Image                           | Port            | Vai trò                                 |
| ----------- | ------------------------------- | --------------- | --------------------------------------- |
| `backend`   | Python 3.11 (build)             | 8000            | FastAPI API server                      |
| `worker`    | Python 3.11 (build)             | —               | Kafka consumer, chạy LangGraph pipeline |
| `frontend`  | Node 18 → Nginx (build)         | 80              | React SPA                               |
| `mongo`     | mongo:6.0                       | 27017           | Lưu trữ users, reports, chat history    |
| `redis`     | redis:7.2-alpine                | 6379            | Cache, rate limit, session, job state   |
| `zookeeper` | confluentinc/cp-zookeeper:7.6.1 | —               | Kafka coordinator                       |
| `kafka`     | confluentinc/cp-kafka:7.6.1     | 9094 (external) | Message queue cho async jobs            |

> Backend và worker chia sẻ volume `hf_model_cache` để HuggingFace model (embeddings, cross-encoder) chỉ tải một lần duy nhất.

---

## Multi-Agent Pipeline — Cơ chế chi tiết

### Luồng xử lý

```
User POST /api/v1/stock/analyze/{ticker}
        │
        ▼
Backend tạo job_id → đẩy message vào Kafka topic "stock_analysis_tasks"
        │
        ▼
Worker consume message → gọi run_analysis(ticker)
        │
        ▼
LangGraph compiled graph (_graph.ainvoke)
        │
  ┌─────┴──────────────────────────────────────────────┐
  │                   StockState (TypedDict)             │
  │  ticker │ research_data │ analysis_data             │
  │  recommendation │ error │ progress_cb               │
  └──────────────────────────────────────────────────────┘
        │
        ├─── Node 1: Market Researcher ──────────────────┐
        │    asyncio.gather(get_prices, get_news)        │
        │    VN: race(TCBS API, Yahoo .VN) → ai nhanh hơn│
        │    US: Yahoo Finance → Alpha Vantage fallback  │
        │    → research_data vào StockState              │
        │    [progress_cb notify: "Đã thu thập X ngày·Y tin"]
        │                                                 │
        ├─ conditional edge: error? → END               ◄┘
        │
        ├─── Node 2: Financial Analyst ─────────────────┐
        │    analyze_financials(research_data)           │
        │    Thuần thuật toán, không LLM:                │
        │    SMA(5/20/50/100) · EMA(12/26)               │
        │    RSI-14 (Wilder's Smoothed)                  │
        │    MACD(12/26/9) + Signal + Histogram          │
        │    Bollinger Bands (20 kỳ, ±2σ)               │
        │    ATR-14 · ADX-14 (+DI/−DI)                  │
        │    Volume spike · Trend 5 nến                  │
        │    Sentiment tổng hợp từ news                  │
        │    → analysis_data vào StockState              │
        │    [progress_cb notify: "RSI=X · MACD=Y · ADX=Z"]
        │                                                 │
        ├─ conditional edge: error? → END               ◄┘
        │
        └─── Node 3: Investment Advisor ────────────────┐
             get_recommendation(analysis_data)           │
             → TechnicalAnchor (rule engine, không LLM) │
             → LLM Synthesis (Gemini → Groq → Anchor)   │
             → recommendation vào StockState             │
             [progress_cb notify: "Điểm X/10 · Khuyến nghị: Y"]
                                                         │
        ▼                                               ◄┘
Backend lưu report → MongoDB
Frontend poll status/{job_id} → nhận kết quả hoàn chỉnh
```

### TechnicalAnchor — Rule Engine (không LLM)

`InvestmentRuleEngine` là **Single Source of Truth** cho mọi khuyến nghị. LLM chỉ được phép giải thích, không được tự tạo khuyến nghị.

**Scoring model (max ±8):**

| Yếu tố        | Bullish                        | Bearish                          | Logic                   |
| ------------- | ------------------------------ | -------------------------------- | ----------------------- |
| **RSI**       | +2 (< 30 oversold) / +1 (< 45) | −2 (> 70 overbought) / −1 (> 55) | RSI-14 Wilder           |
| **MACD**      | +2 (golden cross)              | −2 (death cross)                 | MACD(12,26,9) crossover |
| **SMA Trend** | +2 (price > SMA20 > SMA50)     | −2 (ngược lại)                   | Xếp hàng MA             |
| **Bollinger** | +1 (dưới lower band)           | −1 (trên upper band)             | BB(20, 2σ)              |
| **Volume**    | +1 (spike + uptrend)           | −1 (spike + downtrend)           | Khuếch đại xu hướng     |

**Quyết định:**

- `score ≥ 4` → **BUY STRONG**
- `score ≥ 2` → **BUY MODERATE**
- `score ≤ −4` → **SELL STRONG**
- `score ≤ −2` → **SELL MODERATE**
- còn lại → **HOLD**

**Target price và Stop-loss** tính động từ ATR-14 — không hardcode.

### LLM Fallback Chain

```
Gemini 2.5 Flash  (primary)
      │ rate limit / 503?
      ▼
Groq Llama-3.3-70b  (cross-provider fallback — Google sập vẫn chạy được)
      │ cũng fail?
      ▼
Pre-computed TechnicalAnchor text  (luôn available, 0 LLM)
```

Retry logic: chỉ retry các lỗi `429 / 503 / quota_exceeded / rate_limit`, không retry `401 / 404`.

---

## RAG Chatbot — Cơ chế chi tiết

### Luồng xử lý 8 bước

```
User gửi query
        │
        ▼
┌──────────────────────────────────────────────────────────────┐
│ Bước 1 — INPUT GUARD                                         │
│  • Validate độ dài, ký tự hợp lệ                            │
│  • Phát hiện Prompt Injection (regex + LLM judge)            │
│  • Mask dữ liệu nhạy cảm (số tài khoản, CMND…)              │
│  • Từ chối ngay nếu vi phạm → không tốn LLM                 │
└──────────────────┬───────────────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────────────┐
│ Bước 2 — SHORTCUT ROUTER (0 LLM call)                       │
│  6 regex pattern được kiểm tra theo thứ tự ưu tiên:         │
│  • Giá cổ phiếu: "giá FPT", "TCB hôm nay", "VNM bao nhiêu" │
│  • So sánh giá: "so sánh FPT VNM", "FPT vs HPG"            │
│  • Top BUY: "top mã buy hôm nay", "danh sách khuyến nghị"   │
│  • Phân tích kỹ thuật: "RSI FPT", "MACD VNM"               │
│  • Tổng quan thị trường: "VN-Index hôm nay", "thị trường"   │
│  • Tin tức: "tin tức FPT", "FPT có tin gì mới"              │
│  Match → gọi data source trực tiếp → stream kết quả (0 LLM) │
└──────────────────┬───────────────────────────────────────────┘
                   │ không match shortcut
                   ▼
┌──────────────────────────────────────────────────────────────┐
│ Bước 3 — INTENT ROUTER                                      │
│  Phân loại query thành 4 intent:                            │
│  • ADVISORY   — tư vấn mua/bán, khuyến nghị cụ thể         │
│  • KNOWLEDGE  — kiến thức chung về chứng khoán              │
│  • COMPLAINT  — khiếu nại, phản ánh dịch vụ                 │
│  • OUT_OF_SCOPE — ngoài phạm vi hỗ trợ                      │
│  Fast-path: regex rule-based (0 LLM)                        │
│  Fallback: LLM judge chỉ khi regex không chắc chắn          │
└──────────────────┬───────────────────────────────────────────┘
                   │ intent xác định
                   ▼
┌──────────────────────────────────────────────────────────────┐
│ Bước 4 — NATIVE TOOL CALLING Round 1                        │
│  LLM nhận query + danh sách 8 tool definitions              │
│  LLM tự chọn tool(s) phù hợp (hoặc bị pre-route bởi        │
│  intent/shortcut để tiết kiệm quota)                        │
│                                                              │
│  8 tools:                                                    │
│  get_price_info          get_technical_analysis             │
│  get_rag_advisory        get_rag_knowledge                  │
│  get_faq                 get_market_overview                │
│  get_stock_news          get_top_buy_list                   │
│                                                              │
│  Tools được gọi song song (asyncio.gather)                  │
└──────────────────┬───────────────────────────────────────────┘
                   │ tool results
                   ▼
┌──────────────────────────────────────────────────────────────┐
│ Bước 5 — RETRIEVAL & CRAG EVAL (Corrective RAG)             │
│  Hybrid Search:                                              │
│    Dense: paraphrase-multilingual-MiniLM-L12-v2 (384-dim)   │
│    Sparse: BM25 (rank_bm25)                                  │
│    Fusion: RRF (Reciprocal Rank Fusion)                      │
│    Rerank: Cross-Encoder (ms-marco → mmarco → BGE fallback) │
│                                                              │
│  CRAG Evaluator:                                             │
│    Heuristic score từ similarity + keyword match            │
│    → RELEVANT / AMBIGUOUS / IRRELEVANT                      │
│    LLM judge CHỈ khi AMBIGUOUS (~25% queries)               │
│    IRRELEVANT → trả INSUFFICIENT_DOCS, không hallucinate    │
└──────────────────┬───────────────────────────────────────────┘
                   │ context đã lọc
                   ▼
┌──────────────────────────────────────────────────────────────┐
│ Bước 6 — LLM SYNTHESIS Round 2                              │
│  Tổng hợp kết quả từ tất cả tools + retrieved context      │
│  System prompt khác nhau cho mỗi intent pipeline            │
│  TechnicalAnchor được inject vào prompt như "source of      │
│  truth" — LLM chỉ giải thích, không được override           │
└──────────────────┬───────────────────────────────────────────┘
                   │ raw response
                   ▼
┌──────────────────────────────────────────────────────────────┐
│ Bước 7 — OUTPUT GUARD                                       │
│  • Confidence gate: confidence thấp → LOW_CONFIDENCE reply  │
│  • Hallucination check: phát hiện số liệu bịa đặt           │
│  • Mandatory disclaimer inject vào MỌI advisory response    │
│  • ESCALATION nếu câu hỏi vượt quá khả năng AI             │
└──────────────────┬───────────────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────────────┐
│ Bước 8 — AUDIT LOG                                          │
│  Ghi log mọi bước (intent, tools used, crag score,          │
│  llm provider, latency) → MongoDB + correlation ID          │
└──────────────────┬───────────────────────────────────────────┘
                   │
                   ▼
           Stream SSE → Frontend
```

### Pinecone — 3 Namespaces độc lập

| Namespace           | Nội dung                                         | Pipeline dùng |
| ------------------- | ------------------------------------------------ | ------------- |
| `internal-advisory` | Báo cáo phân tích nội bộ, khuyến nghị chuyên gia | ADVISORY      |
| `public-knowledge`  | Kiến thức chứng khoán, thuật ngữ, hướng dẫn      | KNOWLEDGE     |
| `faq-complaint`     | FAQ, quy trình xử lý khiếu nại                   | COMPLAINT     |

Mỗi pipeline chỉ truy vấn đúng namespace của mình — tránh cross-contamination giữa tư vấn nội bộ và thông tin công khai.

### Hierarchical Chunking

```
PDF document
      │
      ▼
Parent chunk (3000 chars) — lưu MongoDB
      │
      ├─► Child chunk 1 (1500 chars) ─► Embed → Pinecone (id → parent_id)
      ├─► Child chunk 2 (1500 chars) ─► Embed → Pinecone
      └─► Child chunk 3 (1500 chars) ─► Embed → Pinecone

Khi retrieve:
  1. Dense search tìm child chunks có similarity cao
  2. Từ child_id → tra parent_id → load parent chunk từ MongoDB
  3. Đưa parent chunk (ngữ cảnh đầy đủ) vào LLM
  → Embed chính xác, context đủ rộng
```

### Redis — Các lớp cache

| Key pattern               | TTL | Dữ liệu                                            |
| ------------------------- | --- | -------------------------------------------------- |
| `rag_cache:{md5(query)}`  | 2h  | Response cache (chỉ cache khi không có history)    |
| `conv:{session_id}`       | 2h  | Conversation history server-side (max 8 turns)     |
| `ticker_ctx:{session_id}` | 2h  | Mã cổ phiếu đang thảo luận trong session           |
| `rate:{user_id}:stream`   | 60s | Rate limit stream (30 req/min)                     |
| `rate:{user_id}:query`    | 60s | Rate limit query (60 req/min)                      |
| `job:{job_id}`            | 1h  | Trạng thái Kafka job (pending/running/done/failed) |

---

## Công nghệ sử dụng

| Layer                | Công nghệ                                                                                |
| -------------------- | ---------------------------------------------------------------------------------------- |
| **AI Orchestration** | LangGraph (StateGraph, TypedDict state, conditional edges)                               |
| **LLM Primary**      | Google Gemini 2.5 Flash (`gemini-2.5-flash`)                                             |
| **LLM Fallback**     | Groq Llama-3.3-70b (`langchain-groq`) → Pre-computed TechnicalAnchor                     |
| **Embeddings**       | `paraphrase-multilingual-MiniLM-L12-v2` (384-dim, HuggingFace, CPU)                      |
| **Reranking**        | Cross-Encoder: `ms-marco-MiniLM-L-6-v2` → `mmarco-mMiniLMv2` → `BAAI/bge-reranker-v2-m3` |
| **Vector Store**     | Pinecone (3 namespaces, cosine similarity)                                               |
| **Hybrid Search**    | Dense (cosine) + BM25 (`rank_bm25`) + RRF Fusion                                         |
| **Stock Data**       | TCBS API (VN) → Yahoo Finance (`yfinance`) → Alpha Vantage                               |
| **News**             | VnNews/CafeF RSS aggregator, Alpha Vantage NEWS_SENTIMENT                                |
| **Backend API**      | FastAPI + Uvicorn (Python 3.11)                                                          |
| **Database**         | MongoDB 6 (motor async driver)                                                           |
| **Cache & Session**  | Redis 7.2 (aioredis)                                                                     |
| **Message Queue**    | Apache Kafka (Confluent 7.6) + aiokafka                                                  |
| **Authentication**   | JWT (python-jose) + bcrypt (passlib)                                                     |
| **Frontend**         | React 18 + Vite + React Router v7                                                        |
| **Charts**           | Recharts (LineChart + MA5/MA20 overlay)                                                  |
| **Animations**       | Framer Motion                                                                            |
| **Container**        | Docker + Docker Compose (7 services)                                                     |
| **Observability**    | Prometheus (`prometheus-fastapi-instrumentator`) + Correlation ID                        |

---

## Cài đặt và chạy

### Yêu cầu

- Docker Desktop 24+ và Docker Compose v2
- API keys: Gemini, Pinecone (xem mục [Cấu hình môi trường](#cấu-hình-môi-trường))
- _(Tuỳ chọn local)_ Python 3.11+, Node 18+

### Cách 1 — Docker Compose (khuyên dùng)

```bash
# 1. Clone repo
git clone <repo-url>
cd "He thong Multi-Agent Phan tich va Khuyen nghi Ma Co phieu"

# 2. Cấu hình môi trường
cp .env.example .env
# Mở .env và điền API keys (xem mục Cấu hình bên dưới)

# 3. Khởi chạy toàn bộ stack
docker-compose up --build

# Lần sau không cần build lại
docker-compose up
```

Sau khi khởi động xong (~2-3 phút để Kafka và HuggingFace model warm-up):

| Service            | URL                         |
| ------------------ | --------------------------- |
| Frontend           | http://localhost:80         |
| Backend API        | http://localhost:8000       |
| API Docs (Swagger) | http://localhost:8000/docs  |
| API Docs (ReDoc)   | http://localhost:8000/redoc |

### Cách 2 — Local (không dùng Docker)

Yêu cầu MongoDB, Redis, Kafka đang chạy.

```bash
# Backend
cd backend
python -m venv venv

# Windows
.\venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

```bash
# Frontend (terminal riêng)
cd frontend
npm install
npm run dev   # chạy trên http://localhost:5173
```

### Tài khoản mặc định

| Role  | Username | Password                              |
| ----- | -------- | ------------------------------------- |
| Admin | `admin`  | giá trị `ADMIN_PASSWORD` trong `.env` |
| User  | `user`   | giá trị `USER_PASSWORD` trong `.env`  |

---

## Cấu hình môi trường

```bash
cp .env.example .env
```

### Biến bắt buộc

```env
# Security — đổi bắt buộc trước khi deploy
SECRET_KEY=your-super-secret-key-min-32-chars
ADMIN_PASSWORD=ChangeMe@2025
USER_PASSWORD=UserPass@2025

# LLM
GEMINI_API_KEY=       # Google AI Studio: https://aistudio.google.com/
GROQ_API_KEY=         # https://console.groq.com (LLM fallback, tuỳ chọn)

# Vector Store
PINECONE_API_KEY=     # https://app.pinecone.io
PINECONE_INDEX_NAME=  # Tên index (dimension=384, metric=cosine)

# Stock Data
ALPHA_VANTAGE_API_KEY=  # https://www.alphavantage.co (dự phòng US data)
```

### Biến tuỳ chọn (Docker Compose tự set)

```env
# Infrastructure — giá trị mặc định cho Docker Compose
MONGO_URI=mongodb://mongo:27017/stockdb
REDIS_URL=redis://redis:6379/0
KAFKA_BROKER_URL=kafka:9092

# JWT
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60   # 1 giờ

# CORS
BACKEND_CORS_ORIGINS=["http://localhost:3000","http://127.0.0.1:3000"]
```

### Tạo Pinecone Index

1. Đăng nhập [Pinecone Console](https://app.pinecone.io/)
2. Tạo index mới với thông số:
   - **Dimensions**: `384`
   - **Metric**: `cosine`
   - **Cloud/Region**: AWS us-east-1 (free tier)
3. Copy **API key** và **Index name** vào `.env`

---

## API Reference

### Authentication

```
POST /api/v1/auth/register
  Body: { "username": "...", "password": "..." }

POST /api/v1/auth/login
  Body: OAuth2 form (username, password)
  Response: { access_token, token_type }

POST /api/v1/auth/refresh
  Header: Authorization: Bearer <token>
  Response: { access_token mới }

GET  /api/v1/auth/me
  Response: thông tin user hiện tại

PUT  /api/v1/auth/profile
  Body: thông tin cập nhật (display_name, investment_style…)

POST /api/v1/auth/forgot-password/verify   xác minh câu hỏi bí mật
POST /api/v1/auth/forgot-password/reset    đặt lại mật khẩu
```

### Stock Analysis (async Kafka job)

```
POST /api/v1/stock/analyze/{ticker}
  Response: { job_id }   — job chạy background qua Kafka

GET  /api/v1/stock/analyze/status/{job_id}
  Response: { status: pending|running|done|failed, result? }

GET  /api/v1/stock/history/     lịch sử phân tích của user
DELETE /api/v1/stock/history    xóa toàn bộ lịch sử
GET  /api/v1/stock/stats/       top mã được tìm nhiều nhất
GET  /api/v1/stock/featured/    mã cổ phiếu nổi bật
```

### RAG Chatbot

```
POST /api/v1/rag/query/
  Body: { "query": "...", "session_id": "..." }
  Response: JSON đồng bộ

POST /api/v1/rag/query/stream
  Body: { "query": "...", "session_id": "..." }
  Response: SSE stream (text/event-stream)

POST /api/v1/rag/query/compare/stream
  Body: { "query": "...", "session_id": "...", "tickers": ["FPT","VNM"] }
  Response: SSE stream so sánh 2 mã

GET  /api/v1/rag/suggestions/        chip gợi ý tài liệu đã upload
GET  /api/v1/rag/metrics/rag-summary  số liệu hiệu quả retrieval
```

### Knowledge Base

```
POST   /api/v1/rag/upload/
  Form: file (PDF), namespace, ticker (tuỳ chọn)
  Response: { doc_id } — embed chạy background

GET    /api/v1/rag/documents/              danh sách tài liệu
DELETE /api/v1/rag/documents/{doc_id}/     xóa tài liệu + vectors Pinecone

POST   /api/v1/rag/documents/{doc_id}/reindex
  Body: { "target_namespace": "public-knowledge" }
  Response: chuyển document sang namespace khác
```

### Chat History

```
POST   /api/v1/rag/chat/save      lưu lịch sử hội thoại
GET    /api/v1/rag/chat/history   lấy history theo session_id
GET    /api/v1/rag/chat/sessions  danh sách sessions của user
DELETE /api/v1/rag/chat/history   xóa history
```

### Quotes

```
GET    /api/v1/quotes/                  danh sách quote
POST   /api/v1/quotes/                  tạo quote (Admin)
PUT    /api/v1/quotes/{quote_id}        cập nhật quote (Admin)
DELETE /api/v1/quotes/{quote_id}        xóa quote (Admin)
GET    /api/v1/quotes/random            lấy quote ngẫu nhiên
GET    /api/v1/quotes/stats/            thống kê hệ thống
GET    /api/v1/quotes/activity-summary/ tóm tắt hoạt động user
```

Xem đầy đủ: **http://localhost:8000/docs**

---

## Cấu trúc thư mục

```
.
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   │   ├── graph.py              # LangGraph StateGraph, 3 nodes, conditional edges
│   │   │   ├── market_researcher.py  # asyncio.gather OHLCV + News, race TCBS/Yahoo
│   │   │   ├── financial_analyst.py  # TA indicators thuần thuật toán
│   │   │   ├── investment_advisor.py # Gọi rule engine + LLM synthesis
│   │   │   └── tools.py
│   │   ├── api/
│   │   │   ├── router.py             # Gộp 4 routers
│   │   │   └── endpoints/
│   │   │       ├── auth.py
│   │   │       ├── stock.py          # Kafka job dispatch
│   │   │       ├── rag.py            # RAG + upload + chat history
│   │   │       └── quotes.py
│   │   ├── core/
│   │   │   ├── config.py             # Pydantic Settings, env-based
│   │   │   ├── security.py           # JWT encode/decode, bcrypt
│   │   │   └── exceptions/
│   │   ├── db/
│   │   │   ├── mongodb.py            # Motor async client
│   │   │   └── redis.py              # aioredis client
│   │   ├── models/                   # Pydantic schemas
│   │   ├── repositories/             # MongoDB CRUD (user, quote, report)
│   │   ├── services/
│   │   │   ├── rag/
│   │   │   │   ├── rag_pipeline.py      # Orchestrator 8 bước, shortcut patterns
│   │   │   │   ├── vector_store.py      # Pinecone wrapper, hybrid search, rerank
│   │   │   │   ├── guardrails.py        # Input/Retrieval/Output guards
│   │   │   │   ├── intent_router.py     # Intent classification (regex + LLM)
│   │   │   │   ├── chat_tools.py        # 8 tool implementations
│   │   │   │   └── pdf_processor.py     # PDF extract → hierarchical chunks
│   │   │   ├── analysis_service.py      # Kafka job handler, gọi LangGraph
│   │   │   ├── llm_provider.py          # Gemini → Groq → Anchor fallback chain
│   │   │   ├── investment_rule_engine.py # TechnicalAnchor, scoring ±8
│   │   │   ├── tcbs_service.py          # TCBS API client (VN stocks)
│   │   │   ├── technical_analysis.py    # SMA/EMA/RSI/MACD/BB/ATR/ADX
│   │   │   ├── vn_news.py               # VnNews/CafeF RSS aggregator
│   │   │   ├── redis_rate_limiter.py    # 30/60 req/min per user
│   │   │   ├── ticker_context_cache.py  # Session ticker Redis cache
│   │   │   ├── auth_service.py          # JWT logic, user CRUD
│   │   │   └── audit_service.py         # Compliance logging
│   │   ├── main.py                   # FastAPI app, lifespan, CORS, metrics
│   │   └── worker.py                 # Kafka consumer loop
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Dashboard.jsx         # Main view
│   │   │   ├── ChatBotWidget.jsx     # SSE streaming chatbot
│   │   │   ├── TechnicalDashboard.jsx # Recharts + MA overlay
│   │   │   ├── AnalysisResult.jsx
│   │   │   ├── HistorySidebar.jsx    # 10 phân tích gần nhất
│   │   │   └── admin/               # KnowledgeBase, QuoteManagement
│   │   ├── pages/
│   │   │   ├── Home.jsx
│   │   │   ├── Login.jsx / Register.jsx
│   │   │   └── AdminDashboard.jsx
│   │   ├── context/AuthContext.jsx   # JWT token state
│   │   └── main.jsx
│   ├── package.json
│   └── Dockerfile                   # Node build → Nginx serve
├── docker-compose.yml               # 8 services
├── .env.example
├── architecture.md                  # Mermaid diagrams chi tiết
└── README.md
```

---

## Hướng dẫn phát triển

### Thêm Agent mới vào pipeline

1. Tạo `backend/app/agents/new_agent.py`, implement async function nhận và trả `StockState`
2. Đăng ký node trong [graph.py](backend/app/agents/graph.py):

```python
workflow.add_node("new_agent", new_agent_fn)
workflow.add_conditional_edges("analyst", check_error, {"ok": "new_agent", "error": END})
workflow.add_conditional_edges("new_agent", check_error, {"ok": "advisor", "error": END})
```

3. Thêm field mới vào `StockState` TypedDict nếu cần truyền data

### Thêm Tool mới cho RAG

1. Implement async function trong [chat_tools.py](backend/app/services/rag/chat_tools.py)
2. Thêm định nghĩa tool vào `TOOL_DEFINITIONS` (JSON Schema)
3. Tool tự động được LLM phát hiện và gọi trong Round 1

### Upload tài liệu vào Knowledge Base

1. Đăng nhập Admin → Admin Dashboard → Knowledge Base
2. Upload PDF → chọn namespace phù hợp:
   - `internal-advisory`: báo cáo phân tích nội bộ
   - `public-knowledge`: tài liệu giáo dục, thuật ngữ
   - `faq-complaint`: FAQ, quy trình
3. Hệ thống tự động: PDF extract → hierarchical chunk → embed → Pinecone (background)
4. Chatbot dùng tài liệu ngay khi embedding hoàn tất

### Chạy tests

```bash
cd backend
pytest tests/ -v --cov=app --cov-report=html
```

---

## Troubleshooting

### Kafka không kết nối được

```bash
# Kafka cần 30-60s để khởi động hoàn toàn
docker-compose restart backend worker
docker-compose logs kafka  # kiểm tra trạng thái
```

### Pinecone lỗi

**"Index not found"**: Kiểm tra `PINECONE_INDEX_NAME` khớp tên index trên Console, dimension=384, metric=cosine.

**"Quota exceeded"**: Pinecone free tier giới hạn 1 index và 100k vectors.

### LLM không phản hồi

Hệ thống tự động fallback qua 3 levels — nếu cả Gemini lẫn Groq đều fail, vẫn trả về khuyến nghị từ TechnicalAnchor (rule-based, không cần LLM).

### HuggingFace model tải chậm lần đầu

Volume `hf_model_cache` lưu model sau lần tải đầu. Nếu xóa volume, model sẽ tải lại (~500MB).

### Xem logs

```bash
docker-compose logs -f            # tất cả services
docker-compose logs -f backend    # chỉ API server
docker-compose logs -f worker     # chỉ Kafka consumer
```

---

## Kiến trúc chi tiết

Xem [architecture.md](./architecture.md) để có Mermaid diagrams, LLM cost breakdown theo query type, Redis key patterns, Pinecone namespace strategy.
