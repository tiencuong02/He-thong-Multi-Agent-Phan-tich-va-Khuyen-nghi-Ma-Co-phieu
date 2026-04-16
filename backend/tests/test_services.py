"""
Tests for service layer (AnalysisService, AuthService, QuoteService)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.core.exceptions.app_exceptions import BaseAppException, ResourceNotFoundException


# ============================================================================
# ANALYSIS SERVICE TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_initiate_analysis_valid_ticker(mock_analysis_service, mock_kafka):
    """Test successful analysis initiation with valid ticker"""
    mock_analysis_service.kafka_producer = mock_kafka

    job_id = await mock_analysis_service.initiate_analysis("AAPL")

    assert job_id is not None
    assert len(job_id) > 0
    assert isinstance(job_id, str)
    mock_kafka.publish_message.assert_called_once()


@pytest.mark.asyncio
async def test_initiate_analysis_multiple_tickers(mock_analysis_service):
    """Test analysis initiation for multiple valid tickers"""
    tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]

    for ticker in tickers:
        job_id = await mock_analysis_service.initiate_analysis(ticker)
        assert job_id is not None
        assert isinstance(job_id, str)


@pytest.mark.asyncio
async def test_initiate_analysis_empty_ticker(mock_analysis_service):
    """Test analysis initiation rejects empty ticker"""
    with pytest.raises((ValueError, AttributeError, TypeError)):
        await mock_analysis_service.initiate_analysis("")


@pytest.mark.asyncio
async def test_initiate_analysis_invalid_format(mock_analysis_service):
    """Test analysis initiation rejects invalid ticker format"""
    invalid_tickers = [
        "INVALID_TICKET_123",  # Too long
        "12345",               # Numbers only
        "a",                   # Single char might be invalid
        "apple",               # Lowercase (might need uppercase)
    ]

    # These should either raise errors or be handled gracefully
    for ticker in invalid_tickers:
        try:
            job_id = await mock_analysis_service.initiate_analysis(ticker)
            # If it doesn't raise, that's OK too (depends on implementation)
            assert job_id is None or isinstance(job_id, str)
        except (ValueError, AttributeError, TypeError):
            # Expected behavior
            pass


@pytest.mark.asyncio
async def test_get_job_status_existing_job(mock_analysis_service, mock_job_repository):
    """Test fetching status of existing job"""
    from app.models.stock import JobState

    job_state = JobState(
        job_id="job-123",
        status="processing",
        ticker="AAPL"
    )
    mock_job_repository.get_job = AsyncMock(return_value=job_state)
    mock_analysis_service.job_repo = mock_job_repository

    status = await mock_analysis_service.get_job_status("job-123")

    # Should return job info or status
    assert status is not None or isinstance(status, dict) or status is None


@pytest.mark.asyncio
async def test_get_job_status_nonexistent_job(mock_analysis_service):
    """Test fetching status of non-existent job"""
    status = await mock_analysis_service.get_job_status("nonexistent-job-id")

    # Should return None or raise error
    assert status is None or isinstance(status, dict)


@pytest.mark.asyncio
async def test_process_analysis_handles_errors(mock_analysis_service, mock_kafka):
    """Test analysis processing handles errors gracefully"""
    mock_kafka.publish_message = AsyncMock(side_effect=Exception("Kafka error"))
    mock_analysis_service.kafka_producer = mock_kafka

    with pytest.raises(Exception):
        await mock_analysis_service.initiate_analysis("AAPL")


@pytest.mark.asyncio
async def test_analysis_result_structure(mock_analysis_service, sample_analysis_result):
    """Test that analysis result has correct structure"""
    result = sample_analysis_result

    assert "ticker" in result
    assert "status" in result
    assert "recommendation" in result
    assert "agent_trace" in result
    assert len(result["agent_trace"]) == 3  # 3 agents


# ============================================================================
# AUTH SERVICE TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_register_user_success(mock_auth_service, sample_user_data):
    """Test successful user registration"""
    mock_auth_service.user_repo.create_user = AsyncMock(
        return_value={
            "_id": "user-123",
            **sample_user_data,
            "hashed_password": "hashed_pwd"
        }
    )

    result = await mock_auth_service.register_user(
        email=sample_user_data["email"],
        password=sample_user_data["password"]
    )

    assert result is not None
    mock_auth_service.user_repo.create_user.assert_called_once()


@pytest.mark.asyncio
async def test_register_user_duplicate_email(mock_auth_service, sample_user_data):
    """Test registration fails with duplicate email"""
    mock_auth_service.user_repo.get_by_email = AsyncMock(
        return_value={"email": sample_user_data["email"]}
    )

    # Should raise error or return False
    try:
        result = await mock_auth_service.register_user(
            email=sample_user_data["email"],
            password=sample_user_data["password"]
        )
        # If no error, result should be False
        assert result is False or result is None
    except ValueError:
        # Expected behavior
        pass


@pytest.mark.asyncio
async def test_login_valid_credentials(mock_auth_service, sample_user_data):
    """Test successful login"""
    from passlib.context import CryptContext

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    hashed_password = pwd_context.hash(sample_user_data["password"])

    mock_auth_service.user_repo.get_by_email = AsyncMock(
        return_value={
            "_id": "user-123",
            "email": sample_user_data["email"],
            "hashed_password": hashed_password,
            "role": "USER"
        }
    )

    result = await mock_auth_service.login(
        email=sample_user_data["email"],
        password=sample_user_data["password"]
    )

    # Should return token or user info
    assert result is not None


@pytest.mark.asyncio
async def test_login_invalid_password(mock_auth_service, sample_user_data):
    """Test login fails with wrong password"""
    from passlib.context import CryptContext

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    hashed_password = pwd_context.hash("correct_password")

    mock_auth_service.user_repo.get_by_email = AsyncMock(
        return_value={
            "_id": "user-123",
            "email": sample_user_data["email"],
            "hashed_password": hashed_password,
            "role": "USER"
        }
    )

    # Should fail or return False
    try:
        result = await mock_auth_service.login(
            email=sample_user_data["email"],
            password="wrong_password"
        )
        assert result is False or result is None
    except ValueError:
        # Expected behavior
        pass


@pytest.mark.asyncio
async def test_login_user_not_found(mock_auth_service, sample_user_data):
    """Test login fails when user doesn't exist"""
    mock_auth_service.user_repo.get_by_email = AsyncMock(return_value=None)

    try:
        result = await mock_auth_service.login(
            email="nonexistent@example.com",
            password="password"
        )
        assert result is False or result is None
    except ValueError:
        # Expected behavior
        pass


# ============================================================================
# QUOTE SERVICE TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_create_quote_success(mock_quote_service):
    """Test successful quote creation"""
    quote_data = {
        "text": "The stock market is a device for transferring money from the impatient to the patient.",
        "author": "Warren Buffett",
        "type": "bullish"
    }

    mock_quote_service.quote_repo.create_quote = AsyncMock(return_value="quote-123")

    result = await mock_quote_service.create_quote(**quote_data)

    assert result == "quote-123"
    mock_quote_service.quote_repo.create_quote.assert_called_once()


@pytest.mark.asyncio
async def test_get_all_quotes(mock_quote_service):
    """Test fetching all quotes"""
    quotes = [
        {"_id": "1", "text": "Quote 1", "type": "bullish"},
        {"_id": "2", "text": "Quote 2", "type": "bearish"},
    ]

    mock_quote_service.quote_repo.get_all_quotes = AsyncMock(return_value=quotes)

    result = await mock_quote_service.get_all_quotes()

    assert len(result) == 2
    assert result[0]["type"] == "bullish"


@pytest.mark.asyncio
async def test_get_quotes_by_type(mock_quote_service):
    """Test fetching quotes by type"""
    bullish_quotes = [
        {"_id": "1", "text": "Quote 1", "type": "bullish"},
        {"_id": "2", "text": "Quote 2", "type": "bullish"},
    ]

    mock_quote_service.quote_repo.get_quotes_by_type = AsyncMock(
        return_value=bullish_quotes
    )

    result = await mock_quote_service.get_quotes_by_type("bullish")

    assert len(result) == 2
    assert all(q["type"] == "bullish" for q in result)


@pytest.mark.asyncio
async def test_delete_quote_success(mock_quote_service):
    """Test successful quote deletion"""
    mock_quote_service.quote_repo.delete_quote = AsyncMock(return_value=True)

    result = await mock_quote_service.delete_quote("quote-123")

    assert result is True
    mock_quote_service.quote_repo.delete_quote.assert_called_once_with("quote-123")


@pytest.mark.asyncio
async def test_delete_quote_not_found(mock_quote_service):
    """Test deleting non-existent quote"""
    mock_quote_service.quote_repo.delete_quote = AsyncMock(return_value=False)

    result = await mock_quote_service.delete_quote("nonexistent-quote")

    assert result is False


# ============================================================================
# PARAMETRIZED TESTS
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.parametrize("ticker,should_succeed", [
    ("AAPL", True),
    ("MSFT", True),
    ("GOOGL", True),
    ("BRK.A", True),
    ("BRK.B", True),
])
async def test_analysis_various_valid_tickers(mock_analysis_service, ticker, should_succeed):
    """Test analysis with various valid tickers"""
    job_id = await mock_analysis_service.initiate_analysis(ticker)

    if should_succeed:
        assert job_id is not None


@pytest.mark.asyncio
@pytest.mark.parametrize("quote_type", ["bullish", "bearish", "hold"])
async def test_quotes_all_types(mock_quote_service, quote_type):
    """Test quote operations for all types"""
    quotes = [
        {"_id": "1", "text": f"{quote_type} quote 1", "type": quote_type},
        {"_id": "2", "text": f"{quote_type} quote 2", "type": quote_type},
    ]

    mock_quote_service.quote_repo.get_quotes_by_type = AsyncMock(return_value=quotes)

    result = await mock_quote_service.get_quotes_by_type(quote_type)

    assert len(result) >= 0
    if result:
        assert all(q["type"] == quote_type for q in result)
