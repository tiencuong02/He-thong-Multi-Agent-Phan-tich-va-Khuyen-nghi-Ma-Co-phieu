# Multi-Agent Stock Analysis Platform

Hệ thống phân tích cổ phiếu sử dụng kiến trúc Đa tác nhân (Multi-Agent) với **LangGraph**, FastAPI, MongoDB, Redis, Kafka và React. Cùng với đó là một hệ thống **Advanced Agentic RAG Chatbot** chuyên nghiệp.

## Tính năng nổi bật

### Phân tích cổ phiếu (Multi-Agent Pipeline)

- **LangGraph StateGraph**: Điều phối 3 agent tuần tự qua shared state (`StockState`), dừng tự động khi gặp lỗi ở bất kỳ node nào.
- **Market Researcher**: Thu thập đồng thời giá lịch sử (`TIME_SERIES_DAILY`) và tin tức (`NEWS_SENTIMENT`) qua Alpha Vantage bằng `asyncio.gather`.
- **Financial Analyst**: Tính toán toàn bộ chỉ số kỹ thuật thuần thuật toán — SMA (MA5/MA20/MA50/MA100), EMA12/EMA26, RSI-14 (Wilder's Smoothed), MACD (12/26/9), Bollinger Bands (20 kỳ, 2σ), ATR-14, ADX-14 (+DI/−DI), xu hướng 5 nến, biến động khối lượng và tổng hợp sentiment tin tức.
- **Investment Advisor**: Khuyến nghị Buy/Hold/Sell bằng **rule-based multi-factor scoring** (không dùng LLM) — thang điểm −10→+10 qua 8 yếu tố; target price và stop-loss động tính từ ATR.
- **Distributed Task Queue**: Xử lý bất đồng bộ qua Kafka, theo dõi trạng thái job qua Redis.

### Xác thực & Phân quyền

- **OAuth2 Authentication**: Đăng nhập/Đăng ký với JWT token.
- **Role-Based Access Control (RBAC)**: Hai vai trò — **USER** và **ADMIN**.
- **User Profile Management**: Quản lý thông tin cá nhân và phong cách đầu tư.

### AI Chatbot & Advanced RAG

- **Agentic Pipeline**: Trang bị 3 lớp Guardrails (Input, Retrieval, Output), Intent Router và CRAG (Corrective RAG) Evaluator để chống Hallucination và Prompt Injection.
- **Hybrid Search & Reranking**: Kết hợp Semantic Search (`paraphrase-multilingual-MiniLM-L12-v2`) + Keyword Search (BM25) + RRF + Cross-Encoder Reranking (`bge-reranker-v2-m3` / `mmarco-mMiniLMv2`) giúp tra cứu tài liệu cực kì chính xác.
- **Multi-Namespace Pinecone**: Dữ liệu được cô lập bảo mật vào 3 ngăn: `internal-advisory` (Tư vấn), `public-knowledge` (Kiến thức) và `faq-complaint` (Khiếu nại).
- **Tool Calling**: Chatbot tự động gọi các tool realtime (giá thị trường, phân tích kỹ thuật, tin tức, tra cứu PDF) để tổng hợp câu trả lời.
- **Streaming Responses**: Server-Sent Events (SSE) truyền phát realtime mượt mà.

### Admin Dashboard

- **Tổng quan hệ thống**: Top stocks, recommendation trends.
- **Knowledge Base Management**: Upload/quản lý tài liệu PDF. Xử lý Hierarchical Chunking và embedding đa luồng (Background Worker).
- **Quote Management**: Tạo, sửa, xóa quote cảm hứng.
- **User Activity Analytics**: Tần suất truy cập, lịch sử hoạt động gần đây, top cổ phiếu được tìm nhiều nhất.

### Frontend

- **React 18 + Vite**: Giao diện hiện đại, tách biệt logic (Custom Hooks) và UI (Components).
- **Biểu đồ giá**: Recharts LineChart hiển thị giá đóng cửa + MA5/MA20 overlay, 60 ngày gần nhất.
- **Responsive Design**: Tailwind CSS + Framer Motion animations.

## Công nghệ sử dụng

| Layer | Công nghệ |
|---|---|
| **AI Orchestration** | LangGraph (StateGraph) |
| **Agent Scoring** | Rule-based multi-factor (không dùng LLM) |
| **LLM Synthesis** | Google Gemini 2.5 Flash (`langchain-google-genai`) |
| **Embeddings** | `paraphrase-multilingual-MiniLM-L12-v2` (384-dim, HuggingFace) |
| **Reranking** | Cross-Encoder (`bge-reranker-v2-m3`, `mmarco-mMiniLMv2`) |
| **RAG Store** | LangChain + Pinecone (Multi-Namespace) |
| **Stock Data** | Alpha Vantage (TIME_SERIES_DAILY + NEWS_SENTIMENT) |
| **Backend API** | FastAPI + Uvicorn |
| **Task Queue** | Apache Kafka + aiokafka |
| **Cache** | Redis 7 |
| **Database** | MongoDB 6 (motor async driver) |
| **Authentication** | JWT / OAuth2 (python-jose, passlib) |
| **Frontend** | React 18, Vite, React Router v7 |
| **Charts** | Recharts (LineChart + MA overlay) |
| **Animations** | Framer Motion |
| **Container** | Docker + Docker Compose |

## Hướng dẫn cài đặt và Chạy

### 1. Chuẩn bị môi trường (chỉ làm 1 lần)

Tạo file `.env` tại thư mục `backend/` dựa trên `.env.example`:

```bash
cp backend/.env.example backend/.env
# Điền các API keys vào backend/.env
```

Cài đặt dependencies backend:

```bash
cd backend
pip install -r requirements.txt
```

### 2. Khởi chạy hệ thống

**Cách 1: Docker (khuyên dùng)**

```bash
docker-compose up --build
```

**Cách 2: Chạy local (manual)**

```bash
# Terminal 1 — Backend API
cd backend
uvicorn app.main:app --reload

# Terminal 2 — Background Worker
cd backend
python -m app.worker

# Terminal 3 — Frontend
cd frontend
npm install
npm run dev
```

Sau khi khởi động:
- Frontend: http://localhost:3000
- Backend API docs: http://localhost:8000/docs

## Kiến trúc hệ thống

Chi tiết xem tại [architecture.md](./architecture.md).
