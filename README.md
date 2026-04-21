# Multi-Agent Stock Analysis Platform

Hệ thống phân tích cổ phiếu sử dụng kiến trúc Đa tác nhân (Multi-Agent) với **LangGraph**, FastAPI, MongoDB, Redis, Kafka và React.

## Tính năng nổi bật

### Phân tích cổ phiếu (Multi-Agent Pipeline)

- **LangGraph StateGraph**: Điều phối 3 agent tuần tự qua shared state (`StockState`), dừng tự động khi gặp lỗi.
- **Market Researcher**: Thu thập giá lịch sử (yfinance) và tin tức thị trường.
- **Financial Analyst**: Tính MA5/MA20/MA50/MA100, xu hướng, biến động khối lượng và sentiment (TextBlob).
- **Investment Advisor**: Kết hợp phân tích với Gemini LLM để tạo khuyến nghị Buy/Hold/Sell.
- **Distributed Task Queue**: Xử lý bất đồng bộ qua Kafka, theo dõi trạng thái job qua Redis.

### Xác thực & Phân quyền

- **OAuth2 Authentication**: Đăng nhập/Đăng ký với JWT token.
- **Role-Based Access Control (RBAC)**: Hai vai trò — **USER** và **ADMIN**.
- **User Profile Management**: Quản lý thông tin cá nhân và phong cách đầu tư.

### AI Chatbot & RAG

- **RAG Pipeline**: HuggingFace embeddings + Pinecone vector store + Gemini LLM.
- **PDF Knowledge Base** (Admin Only): Upload và xử lý PDF vào vector store.
- **Streaming Responses**: Server-Sent Events (SSE) để truyền phát real-time.
- **Conversation History**: Duy trì ngữ cảnh hội thoại giữa các lượt hỏi.

### Admin Dashboard

- **Tổng quan hệ thống**: Top stocks, recommendation trends.
- **Knowledge Base Management**: Upload/quản lý tài liệu PDF cho chatbot.
- **Quote Management**: Tạo, sửa, xóa quote cảm hứng.
- **User Activity Analytics**: Tần suất truy cập, lịch sử hoạt động gần đây, top cổ phiếu được tìm nhiều nhất.

### Frontend

- **React 18 + Vite**: Giao diện hiện đại, tách biệt logic (Custom Hooks) và UI (Components).
- **Biểu đồ giá**: Recharts với candlestick/line chart.
- **Responsive Design**: Tailwind CSS + Framer Motion animations.

## Công nghệ sử dụng

| Layer | Công nghệ |
|---|---|
| **AI Orchestration** | LangGraph (StateGraph) |
| **LLM** | Google Gemini (`langchain-google-genai`) |
| **Sentiment Analysis** | TextBlob |
| **Stock Data** | yfinance (primary), Alpha Vantage (fallback) |
| **RAG** | LangChain + Pinecone + HuggingFace Embeddings |
| **Backend API** | FastAPI + Uvicorn |
| **Task Queue** | Apache Kafka + aiokafka |
| **Cache** | Redis 7 |
| **Database** | MongoDB 6 (motor async driver) |
| **Authentication** | JWT / OAuth2 (python-jose, passlib) |
| **Frontend** | React 18, Vite, React Router v7 |
| **Charts** | Recharts |
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
