cd

## Component Description

- **React Frontend**: A dashboard providing a user interface for users to enter stock tickers. It displays real-time loading states while agents process data and renders the final report, metrics, and recommendations.
- **FastAPI Backend**: Exposes clean modular REST endpoints (`POST /analyze/{ticker}` and `GET /history`).
- **Kafka Message Broker**: Handles message queuing between FastAPI and the Background Worker for asynchronous task processing.
- **Background Worker**: Consumes jobs from Kafka, updates job status in Redis, and triggers the Agent Orchestrator. It also saves the final results to MongoDB.
- **Redis Cache**: Used for high-speed caching and storing job state. Configured with specific TTLs for auto-expiry:
  - `price` → 10s
  - `history` → 10m
  - `news` → 15m
  - `AI result` → 3m
- **Agent Orchestrator (CrewAI)**: Manages the execution flow, context sharing, and orchestration between the distinct autonomous agents.
- **Market Researcher Agent**: Tasked solely with gathering data like historical price, volume, and the latest news articles.
- **Financial Analyst Agent**: Analyzes news for market sentiment and computes fundamental/technical indicators (e.g., PE ratio, moving averages).
- **Investment Advisor Agent**: The final decision maker that combines raw data and analysis into a human-readable report with a Buy/Hold/Sell recommendation.
- **MongoDB**: The primary database storing user configurations and the historical archive of generated stock reports.
