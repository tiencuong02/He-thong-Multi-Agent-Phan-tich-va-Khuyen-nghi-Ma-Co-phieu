"""
Shared fixtures and configuration for all tests.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock
from fastapi.testclient import TestClient
from app.main import app


# ============================================================================
# FASTAPI TEST CLIENT
# ============================================================================

@pytest.fixture
def client():
    """FastAPI test client for synchronous endpoint testing"""
    return TestClient(app)


# ============================================================================
# DATABASE MOCKS
# ============================================================================

@pytest.fixture
def mock_db():
    """Mock MongoDB connection"""
    db = MagicMock()
    db.users = MagicMock()
    db.reports = MagicMock()
    db.jobs = MagicMock()
    db.quotes = MagicMock()
    return db


@pytest.fixture
def mock_collection():
    """Mock MongoDB collection"""
    collection = MagicMock()
    collection.insert_one = AsyncMock(return_value=Mock(inserted_id="123"))
    collection.find_one = AsyncMock(return_value=None)
    collection.find = AsyncMock(return_value=MagicMock(to_list=AsyncMock(return_value=[])))
    collection.update_one = AsyncMock(return_value=Mock(modified_count=1))
    collection.delete_one = AsyncMock(return_value=Mock(deleted_count=1))
    collection.count_documents = AsyncMock(return_value=0)
    return collection


# ============================================================================
# REDIS MOCKS
# ============================================================================

@pytest.fixture
def mock_redis():
    """Mock Redis connection"""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=1)
    redis.setex = AsyncMock(return_value=True)
    redis.exists = AsyncMock(return_value=0)
    redis.expire = AsyncMock(return_value=1)
    redis.incr = AsyncMock(return_value=1)
    redis.lpush = AsyncMock(return_value=1)
    redis.lrange = AsyncMock(return_value=[])
    redis.disconnect = AsyncMock(return_value=None)
    return redis


# ============================================================================
# KAFKA MOCKS
# ============================================================================

@pytest.fixture
def mock_kafka():
    """Mock Kafka producer"""
    kafka = AsyncMock()
    kafka.publish_message = AsyncMock(return_value=True)
    kafka.get_producer = AsyncMock(return_value=kafka)
    kafka.stop_producer = AsyncMock(return_value=None)
    return kafka


# ============================================================================
# SERVICE MOCKS
# ============================================================================

@pytest.fixture
def mock_analysis_service(mock_db, mock_redis, mock_kafka):
    """Mock AnalysisService"""
    service = MagicMock()
    service.initiate_analysis = AsyncMock(return_value="job-123")
    service.get_job_status = AsyncMock(return_value={"status": "completed"})
    return service


@pytest.fixture
def mock_auth_service(mock_db):
    """Mock AuthService"""
    service = MagicMock()
    service.register_user = AsyncMock(return_value={"id": "user-123", "email": "test@example.com"})
    service.login = AsyncMock(return_value={"access_token": "token-123", "token_type": "bearer"})
    return service


@pytest.fixture
def mock_quote_service(mock_db):
    """Mock QuoteService"""
    service = MagicMock()
    service.create_quote = AsyncMock(return_value="quote-123")
    service.get_all_quotes = AsyncMock(return_value=[])
    service.get_quotes_by_type = AsyncMock(return_value=[])
    service.delete_quote = AsyncMock(return_value=True)
    return service


# ============================================================================
# REPOSITORY MOCKS
# ============================================================================

@pytest.fixture
def mock_user_repository(mock_db):
    """Mock UserRepository"""
    repo = MagicMock()
    repo.create_user = AsyncMock(return_value={
        "_id": "user-123",
        "email": "test@example.com",
        "role": "USER"
    })
    repo.get_by_email = AsyncMock(return_value=None)
    repo.get_by_id = AsyncMock(return_value=None)
    repo.update_user = AsyncMock(return_value=True)
    repo.delete_user = AsyncMock(return_value=True)
    return repo


@pytest.fixture
def mock_report_repository(mock_db):
    """Mock ReportRepository"""
    repo = MagicMock()
    repo.save_report = AsyncMock(return_value="report-123")
    repo.get_report = AsyncMock(return_value=None)
    repo.get_reports_by_user = AsyncMock(return_value=[])
    repo.get_reports_by_ticker = AsyncMock(return_value=[])
    repo.delete_report = AsyncMock(return_value=True)
    repo.delete_old_reports = AsyncMock(return_value=5)
    return repo


@pytest.fixture
def mock_quote_repository(mock_db):
    """Mock QuoteRepository"""
    repo = MagicMock()
    repo.create_quote = AsyncMock(return_value="quote-123")
    repo.get_all_quotes = AsyncMock(return_value=[])
    repo.get_quotes_by_type = AsyncMock(return_value=[])
    repo.update_quote = AsyncMock(return_value=True)
    repo.delete_quote = AsyncMock(return_value=True)
    repo.bulk_insert = AsyncMock(return_value=["quote-1", "quote-2"])
    return repo


@pytest.fixture
def mock_job_repository(mock_redis):
    """Mock JobRepository"""
    repo = MagicMock()
    repo.save_job = AsyncMock(return_value=True)
    repo.get_job = AsyncMock(return_value=None)
    repo.update_job = AsyncMock(return_value=True)
    return repo


# ============================================================================
# SAMPLE DATA
# ============================================================================

@pytest.fixture
def sample_user_data():
    """Sample user data for testing"""
    return {
        "email": "test@example.com",
        "password": "Test1234!",  # Short password (9 bytes - under 72 limit)
        "role": "USER"
    }


@pytest.fixture
def sample_admin_data():
    """Sample admin user data for testing"""
    return {
        "email": "admin@example.com",
        "password": "Admin1234!",  # Short password (10 bytes - under 72 limit)
        "role": "ADMIN"
    }


@pytest.fixture
def sample_stock_data():
    """Sample stock data for testing"""
    return {
        "symbol": "AAPL",
        "prices": [
            {"close": 150, "volume": 2000},
            {"close": 148, "volume": 1800},
        ] + [{"close": 145, "volume": 1500}] * 18,
        "news": [
            {"title": "Apple Revenue Up", "sentiment": "positive"},
            {"title": "Apple Stock Gains", "sentiment": "positive"}
        ],
        "pe_ratio": 25.5,
        "data_points": 20
    }


@pytest.fixture
def sample_analysis_result():
    """Sample analysis result"""
    return {
        "ticker": "AAPL",
        "status": "completed",
        "recommendation": "BUY",
        "confidence": 0.85,
        "fallback_used": False,
        "data_points": 20,
        "agent_trace": [
            {
                "agent": "Market Researcher",
                "status": "completed",
                "tools": ["AlphaVantage", "Playwright"],
                "data_points": 20
            },
            {
                "agent": "Financial Analyst",
                "status": "completed",
                "logic": "Rule-Based",
                "fallback": False
            },
            {
                "agent": "Investment Advisor",
                "status": "completed",
                "logic": "Rule-Based"
            }
        ]
    }


# ============================================================================
# JWT TOKEN FIXTURES
# ============================================================================

@pytest.fixture
def valid_token():
    """Create a valid JWT token"""
    from app.core.security import create_access_token
    from datetime import timedelta

    token = create_access_token(
        subject="test@example.com",
        expires_delta=timedelta(hours=1)
    )
    return token


@pytest.fixture
def admin_token():
    """Create a valid admin JWT token"""
    from app.core.security import create_access_token
    from datetime import timedelta

    token = create_access_token(
        subject="admin@example.com",
        expires_delta=timedelta(hours=1)
    )
    return token


@pytest.fixture
def expired_token():
    """Create an expired JWT token"""
    from app.core.security import create_access_token
    from datetime import timedelta

    token = create_access_token(
        subject="test@example.com",
        expires_delta=timedelta(hours=-1)  # Expired
    )
    return token


# ============================================================================
# PYTEST CONFIGURATION
# ============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def anyio_backend():
    """Configure anyio backend for async tests"""
    return "asyncio"
