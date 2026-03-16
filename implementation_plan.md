# Multi-Agent Stock Analysis Platform Implementation Plan

## Goal Description
Design and implement a multi-agent stock analysis platform using a Python backend (FastAPI, LangGraph/CrewAI) and a React frontend. The platform will use MongoDB for persistent storage and Redis for high-speed caching of real-time stock prices.

## Proposed Changes

### System Architecture
The system employs a 3-agent orchestration pipeline (refer to [architecture.md](file:///d:/DEV/He%20thong%20Multi-Agent%20Phan%20tich%20va%20Khuyen%20nghi%20Ma%20Co%20phieu/architecture.md) for the visual representation).
- **Market Researcher**: Fetches stock data from yfinance and news.
- **Financial Analyst**: Analyzes sentiment from news and computes financial metrics.
- **Investment Advisor**: Synthesizes data and recommends Buy/Hold/Sell.

### API Endpoints
- `POST /analyze/{ticker}`: Input a stock ticker, trigger the multi-agent pipeline, and return the generated report.
- `GET /history`: Fetch past analysis reports and querying history from MongoDB.

### Database Schema
- **MongoDB**: 
  - `users` collection: User profiles and access data.
  - `analyses` collection: Fields include `ticker`, `date`, `report`, `sentiment`.
- **Redis Cache**:
  - Keys format: `stock:{ticker}:price` with a TTL of 5 minutes to prevent redundant API calls.

### Folder Structure Overview

#### [NEW] root directory
- `docker-compose.yml` (Orchestrates all services)
- `README.md` (Project overview and setup instructions)
- `.env` (Environment variables and secrets)

#### [NEW] backend/app/
- `api/` (FastAPI route implementations)
- `agents/` (Definitions for LangGraph/CrewAI agents)
- `db/` (MongoDB and Redis connection configuration)
- `models/` (Pydantic schemas and database models)

#### [NEW] frontend/src/
- `components/` (Reusable UI components like charts and inputs)
- `pages/` (Page views like Dashboard and History)

---

## Verification Plan

### Automated Tests
1. Verify endpoint health and response shapes.
2. Confirm the multi-agent pipeline functions correctly using mock yfinance data and mock search tools.
3. Validate caching mechanisms with Redis TTL.

### Manual Verification
1. Run `docker-compose up` to start all containers.
2. Enter a stock ticker on the React frontend.
3. Verify that the loading state is displayed while the backend agents are processing.
4. Verify that the final Buy/Hold/Sell recommendation report is displayed correctly.
5. Access MongoDB logs to check if queries and reports are being recorded.
