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

### System Architecture (Updated)
- **FastAPI Backend**: Receives requests, publishes an analysis job to Kafka, and immediately returns a 202 Accepted.
- **Kafka**: Message broker separating the FastAPI producer from the LangGraph consumer workers.
- **LangGraph Worker**: Consumes Kafka messages and runs the agent pipeline statelessly, checkpointing state to Redis using the job ID.
- **Redis Cache**: Provides structured TTL caching (CacheService) for application data (price, news, history, ai_result) and LangGraph checkpointing.

### Database Schema & Cache Strategy
- **MongoDB**: 
  - `users` collection: User profiles and access data.
  - `reports` collection: Fields include `job_id`, `ticker`, `date`, `report`, `status`.
- **Redis Cache (CacheService)**:
  - Centralized typed service. Auto-expiry patterns:
    - `price:{ticker}`: 10s
    - `history:{ticker}`: 10m
    - `news:{ticker}`: 15m
    - `ai_result:{jobId}`: 3m
- **LangGraph Checkpoint**:
  - Redis-backed checkpointer using `jobId` as `thread_id`.

### Folder Structure Overview

#### [NEW] root directory
- `docker-compose.yml` (Adds Kafka and Zookeeper services)
- `README.md`
- `.env` (Add `KAFKA_BROKER_URL` and `REDIS_URL`)

#### [NEW] backend/app/
- `api/api_router.py` (FastAPI route implementations)
  - #### [MODIFY] [endpoints.py](file:///d:/DEV/He%20thong%20Multi-Agent%20Phan%20tich%20va%20Khuyen%20nghi%20Ma%20Co%20phieu/backend/app/api/endpoints.py)
    - Add Kafka producer to `POST /analyze/{ticker}`. Returns 202 + `jobId`.
    - Add `GET /analyze/status/{jobId}` endpoint to poll status from Redis.
- `agents/`
  - #### [MODIFY] [orchestrator.py](file:///d:/DEV/He%20thong%20Multi-Agent%20Phan%20tich%20va%20Khuyen%20nghi%20Ma%20Co%20phieu/backend/app/agents/orchestrator.py)
    - Implement LangGraph pipeline using `langgraph-checkpoint-redis` for state management with `jobId` as `thread_id`. Ensure workers are stateless (if CrewAI is kept, wrap it in LangGraph or rewrite agents in LangGraph).
- `db/`
  - #### [NEW] [cache_service.py](file:///d:/DEV/He%20thong%20Multi-Agent%20Phan%20tich%20va%20Khuyen%20nghi%20Ma%20Co%20phieu/backend/app/db/cache_service.py)
    - Create `CacheService` with strict TTLs (`price:` 10s, `history:` 10m, `news:` 15m, `ai_result:` 3m).
  - #### [MODIFY] [redis.py](file:///d:/DEV/He%20thong%20Multi-Agent%20Phan%20tich%20va%20Khuyen%20nghi%20Ma%20Co%20phieu/backend/app/db/redis.py)
    - Export raw redis pool/client for `CacheService` and LangGraph checkpointer.
- #### [NEW] [worker.py](file:///d:/DEV/He%20thong%20Multi-Agent%20Phan%20tich%20va%20Khuyen%20nghi%20Ma%20Co%20phieu/backend/app/worker.py)
  - Kafka consumer that listens to analysis requests and triggers `orchestrator.py` with `jobId`.

#### [NEW] frontend/src/
- `components/` (Reusable UI components like charts and inputs)
- `pages/` (Page views like Dashboard and History)
  - #### [MODIFY] Update React frontend to poll `/analyze/status/{jobId}` after receiving 202 from POST request instead of awaiting synchronously.

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
