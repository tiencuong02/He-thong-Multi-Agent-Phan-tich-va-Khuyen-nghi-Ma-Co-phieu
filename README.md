# Multi-Agent Stock Analysis Platform

Hệ thống phân tích cổ phiếu sử dụng kiến trúc Đa tác nhân (Multi-Agent) với Python, FastAPI, MongoDB, Redis và React.

## Công nghệ sử dụng
- **Backend**: FastAPI, CrewAI, yfinance, TextBlob
- **Frontend**: React, Vite, Lucide-React, Framer Motion, Axios
- **Database**: MongoDB (Lịch sử báo cáo), Redis (Caching real-time)
- **DevOps**: Docker, Docker Compose

## Kiến trúc Multi-Agent
Hệ thống sử dụng 3 Agent phối hợp:
1. **Market Researcher Agent**: Thu thập dữ liệu giá và tin tức từ Yahoo Finance.
2. **Financial Analyst Agent**: Phân tích chỉ số tài chính và đánh giá sentiment từ tin tức.
3. **Investment Advisor Agent**: Tổng hợp báo cáo và đưa ra khuyến nghị Buy/Hold/Sell.

## Hướng dẫn cài đặt và chạy
1. Đảm bảo bạn đã cài đặt Docker và Docker Compose.
2. Tạo file `.env` ở thư mục gốc (nếu chưa có).
3. Chạy lệnh:
   ```bash
   docker-compose up --build
   ```
4. Truy cập Frontend: `http://localhost:80` (hoặc `http://localhost:3000` nếu chạy local dev).
5. Truy cập Backend API: `http://localhost:8000`.

## Testing
Để chạy test cho backend:
```bash
cd backend
pip install -r requirements.txt
pytest
```