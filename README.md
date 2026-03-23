# Multi-Agent Stock Analysis Platform (Professional Refactor)

Hệ thống phân tích cổ phiếu sử dụng kiến trúc Đa tác nhân (Multi-Agent) chuyên nghiệp với FastAPI, MongoDB, Redis, Kafka và React.

## 🚀 Tính năng nổi bật
- **Kiến trúc Đa tác nhân (Multi-Agent)**: Sử dụng `StockAnalysisOrchestrator` để điều phối luồng công việc giữa các Agent chuyên biệt.
- **Browser Automation (Playwright)**: Tự động thu thập tin tức mới nhất từ các nguồn web để bổ sung dữ liệu phân tích.
- **Centralized Configuration**: Quản lý cấu hình tập trung bằng Pydantic Settings, hỗ trợ validate biến môi trường.
- **Distributed Task Queue**: Xử lý tác vụ bất đồng bộ qua Kafka và theo dõi trạng thái job qua Redis.
- **Modular Frontend**: Giao diện React hiện đại, tách biệt logic (Custom Hooks) và UI (Components).

## 🛠️ Công nghệ sử dụng
- **Backend**: FastAPI, Alpha Vantage API, Playwright (Chromium), AIOKafka, Motor (MongoDB).
- **Frontend**: React (Vite), Tailwind CSS (Vanilla CSS modules), Framer Motion, Axios.
- **Infrastructure**: MongoDB (Atlas/Local), Redis (Job State), Kafka Broker.
- **DevOps**: Docker, Docker Compose, Healthchecks.

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