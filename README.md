# Multi-Agent Stock Analysis Platform (Professional Refactor)

Hệ thống phân tích cổ phiếu sử dụng kiến trúc Đa tác nhân (Multi-Agent) chuyên nghiệp với FastAPI, MongoDB, Redis, Kafka và React.

## 🚀 Tính năng nổi bật

<<<<<<< HEAD

### Backend

=======

> > > > > > > b49ee7fa (sua them tam li thi truong)

- **Kiến trúc Đa tác nhân (Multi-Agent)**: Sử dụng `StockAnalysisOrchestrator` để điều phối luồng công việc giữa các Agent chuyên biệt.
- **Browser Automation (Playwright)**: Tự động thu thập tin tức mới nhất từ các nguồn web để bổ sung dữ liệu phân tích.
- **Centralized Configuration**: Quản lý cấu hình tập trung bằng Pydantic Settings, hỗ trợ validate biến môi trường.
- **Distributed Task Queue**: Xử lý tác vụ bất đồng bộ qua Kafka và theo dõi trạng thái job qua Redis.

### Xác thực & Phân quyền

- **OAuth2 Authentication**: Đăng nhập/Đăng ký với JWT token.
- **Role-Based Access Control (RBAC)**: Hai vai trò - **USER** (người dùng thông thường) và **ADMIN** (quản trị viên).
- **User Profile Management**: Quản lý thông tin cá nhân (giới tính, ngày sinh, phong cách đầu tư).
- **Token-based Security**: Sử dụng OAuth2PasswordBearer với JWT token an toàn.

### AI Chatbot & RAG

- **RAG Pipeline (Retrieval-Augmented Generation)**: Kết hợp embedding vectors với LLM để trả lời câu hỏi dựa trên tài liệu.
- **PDF Knowledge Base Management** (Admin Only): Upload, xử lý và lưu trữ PDF vào vector store (Pinecone).
- **Streaming Responses**: Server-Sent Events (SSE) để truyền phát responses real-time.
- **Conversation History**: Duy trì lịch sử hội thoại để đối ngữ ngữ cảnh.
- **Singleton RAG Service**: Khởi tạo một lần tại startup, tiết kiệm tài nguyên.

### Admin Dashboard

- **Dashboard Overview**: Tổng quan thống kê hệ thống (top stocks, recommendation trends).
- **Knowledge Base Management**: Upload/Quản lý tài liệu PDF cho chatbot.
- **Quote Management** (Admin Only): Tạo, sửa, xóa quote cảm hứng.
- **Statistics & Analytics**:
  - Thống kê Quote theo loại (bullish, bearish, hold).
  - Thống kê User Activity (tần suất truy cập, thời gian cuối cùng).
  - Recent Activity Log: Xem lịch sử hoạt động gần đây của người dùng.
  - Top Searched Stocks: Cổ phiếu được tìm kiếm nhiều nhất.

### Frontend

- **Modular Frontend**: Giao diện React hiện đại, tách biệt logic (Custom Hooks) và UI (Components).
- **Authentication UI**: Trang Login/Signup với form validation.
- **User Dashboard**: Dashboard cho người dùng thông thường với phân tích cổ phiếu.
- **Admin Panel**: Giao diện quản lý toàn bộ hệ thống.
- **Responsive Design**: Tailwind CSS + Framer Motion animations.

## 🛠️ Công nghệ sử dụng

## 📥 Hướng dẫn cài đặt và Chạy

### 1. Cài đặt Môi trường (Chỉ làm 1 lần)

- Tạo file `.env` tại thư mục gốc.
- Cài đặt Browser cho Agent (để cào tin tức):
  ```bash
  cd backend
  pip install -r requirements.txt
  python -m playwright install chromium
  ```

### 2. Khởi chạy Hệ thống

- **Cách 1: Sử dụng Docker (Khuyên dùng)**:
  ```bash
  docker-compose up --build
  ```
- **Cách 2: Chạy Local (Manual)**:
  - **Backend (API)**: Bạn vẫn chạy lệnh cũ bình thường:
    ```bash
    cd backend
    uvicorn app.main:app --reload
    ```
  - **Worker** (Bắt buộc để xử lý task):
    ```bash
    cd backend
    python -m app.worker
    ```
  - **Frontend**:
    ```bash
    cd frontend
    npm run dev
    ```

## 📊 Kiến trúc Hệ thống

Chi tiết xem tại [architecture.md](./architecture.md).
