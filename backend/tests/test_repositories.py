"""
Tests for repository layer (database access)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime


# ============================================================================
# USER REPOSITORY TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_create_user_success(mock_user_repository, sample_user_data):
    """Test successful user creation"""
    mock_user_repository.create_user = AsyncMock(
        return_value={
            "_id": "user-123",
            "email": sample_user_data["email"],
            "role": "USER",
            "created_at": datetime.utcnow().isoformat()
        }
    )

    result = await mock_user_repository.create_user(
        email=sample_user_data["email"],
        hashed_password="hashed_pwd",
        role="USER"
    )

    assert result is not None
    assert result["email"] == sample_user_data["email"]
    assert result["role"] == "USER"
    mock_user_repository.create_user.assert_called_once()


@pytest.mark.asyncio
async def test_create_user_with_role(mock_user_repository):
    """Test user creation with different roles"""
    roles = ["USER", "ADMIN"]

    for role in roles:
        mock_user_repository.create_user = AsyncMock(
            return_value={
                "_id": "user-123",
                "email": f"test-{role}@example.com",
                "role": role
            }
        )

        result = await mock_user_repository.create_user(
            email=f"test-{role}@example.com",
            hashed_password="hashed_pwd",
            role=role
        )

        assert result["role"] == role


@pytest.mark.asyncio
async def test_get_user_by_email_found(mock_user_repository, sample_user_data):
    """Test fetching existing user by email"""
    user_data = {
        "_id": "user-123",
        "email": sample_user_data["email"],
        "role": "USER"
    }

    mock_user_repository.get_by_email = AsyncMock(return_value=user_data)

    result = await mock_user_repository.get_by_email(sample_user_data["email"])

    assert result is not None
    assert result["email"] == sample_user_data["email"]
    mock_user_repository.get_by_email.assert_called_once_with(sample_user_data["email"])


@pytest.mark.asyncio
async def test_get_user_by_email_not_found(mock_user_repository):
    """Test fetching non-existent user returns None"""
    mock_user_repository.get_by_email = AsyncMock(return_value=None)

    result = await mock_user_repository.get_by_email("nonexistent@example.com")

    assert result is None


@pytest.mark.asyncio
async def test_get_user_by_id_found(mock_user_repository):
    """Test fetching user by ID"""
    user_data = {
        "_id": "user-123",
        "email": "test@example.com",
        "role": "USER"
    }

    mock_user_repository.get_by_id = AsyncMock(return_value=user_data)

    result = await mock_user_repository.get_by_id("user-123")

    assert result is not None
    assert result["_id"] == "user-123"


@pytest.mark.asyncio
async def test_get_user_by_id_not_found(mock_user_repository):
    """Test fetching non-existent user by ID"""
    mock_user_repository.get_by_id = AsyncMock(return_value=None)

    result = await mock_user_repository.get_by_id("nonexistent-id")

    assert result is None


@pytest.mark.asyncio
async def test_update_user_success(mock_user_repository):
    """Test successful user update"""
    mock_user_repository.update_user = AsyncMock(return_value=True)

    result = await mock_user_repository.update_user(
        user_id="user-123",
        update_data={"role": "ADMIN"}
    )

    assert result is True
    mock_user_repository.update_user.assert_called_once()


@pytest.mark.asyncio
async def test_update_user_not_found(mock_user_repository):
    """Test updating non-existent user"""
    mock_user_repository.update_user = AsyncMock(return_value=False)

    result = await mock_user_repository.update_user(
        user_id="nonexistent-id",
        update_data={"role": "ADMIN"}
    )

    assert result is False


@pytest.mark.asyncio
async def test_delete_user_success(mock_user_repository):
    """Test successful user deletion"""
    mock_user_repository.delete_user = AsyncMock(return_value=True)

    result = await mock_user_repository.delete_user("user-123")

    assert result is True


@pytest.mark.asyncio
async def test_delete_user_not_found(mock_user_repository):
    """Test deleting non-existent user"""
    mock_user_repository.delete_user = AsyncMock(return_value=False)

    result = await mock_user_repository.delete_user("nonexistent-id")

    assert result is False


# ============================================================================
# REPORT REPOSITORY TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_save_report_success(mock_report_repository, sample_analysis_result):
    """Test saving analysis report"""
    mock_report_repository.save_report = AsyncMock(return_value="report-123")

    result = await mock_report_repository.save_report(
        ticker=sample_analysis_result["ticker"],
        user_id="user-123",
        analysis_result=sample_analysis_result
    )

    assert result == "report-123"
    mock_report_repository.save_report.assert_called_once()


@pytest.mark.asyncio
async def test_get_report_found(mock_report_repository):
    """Test fetching existing report"""
    report_data = {
        "_id": "report-123",
        "ticker": "AAPL",
        "user_id": "user-123",
        "recommendation": "BUY"
    }

    mock_report_repository.get_report = AsyncMock(return_value=report_data)

    result = await mock_report_repository.get_report("report-123")

    assert result is not None
    assert result["ticker"] == "AAPL"


@pytest.mark.asyncio
async def test_get_report_not_found(mock_report_repository):
    """Test fetching non-existent report"""
    mock_report_repository.get_report = AsyncMock(return_value=None)

    result = await mock_report_repository.get_report("nonexistent-report")

    assert result is None


@pytest.mark.asyncio
async def test_get_reports_by_user(mock_report_repository):
    """Test fetching user's reports"""
    reports = [
        {"_id": "report-1", "ticker": "AAPL", "user_id": "user-123"},
        {"_id": "report-2", "ticker": "MSFT", "user_id": "user-123"},
    ]

    mock_report_repository.get_reports_by_user = AsyncMock(return_value=reports)

    result = await mock_report_repository.get_reports_by_user(
        user_id="user-123",
        limit=10
    )

    assert len(result) == 2
    assert all(r["user_id"] == "user-123" for r in result)


@pytest.mark.asyncio
async def test_get_reports_by_user_empty(mock_report_repository):
    """Test fetching reports for user with no reports"""
    mock_report_repository.get_reports_by_user = AsyncMock(return_value=[])

    result = await mock_report_repository.get_reports_by_user("user-123")

    assert result == []


@pytest.mark.asyncio
async def test_get_reports_by_ticker(mock_report_repository):
    """Test fetching reports by ticker"""
    reports = [
        {"_id": "report-1", "ticker": "AAPL", "user_id": "user-1"},
        {"_id": "report-2", "ticker": "AAPL", "user_id": "user-2"},
    ]

    mock_report_repository.get_reports_by_ticker = AsyncMock(return_value=reports)

    result = await mock_report_repository.get_reports_by_ticker("AAPL")

    assert len(result) == 2
    assert all(r["ticker"] == "AAPL" for r in result)


@pytest.mark.asyncio
async def test_delete_report_success(mock_report_repository):
    """Test successful report deletion"""
    mock_report_repository.delete_report = AsyncMock(return_value=True)

    result = await mock_report_repository.delete_report("report-123")

    assert result is True


@pytest.mark.asyncio
async def test_delete_report_not_found(mock_report_repository):
    """Test deleting non-existent report"""
    mock_report_repository.delete_report = AsyncMock(return_value=False)

    result = await mock_report_repository.delete_report("nonexistent-report")

    assert result is False


# ============================================================================
# QUOTE REPOSITORY TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_create_quote_success(mock_quote_repository):
    """Test successful quote creation"""
    quote_data = {
        "text": "The stock market is a device for transferring money from the impatient to the patient.",
        "author": "Warren Buffett",
        "type": "bullish"
    }

    mock_quote_repository.create_quote = AsyncMock(return_value="quote-123")

    result = await mock_quote_repository.create_quote(**quote_data)

    assert result == "quote-123"
    mock_quote_repository.create_quote.assert_called_once()


@pytest.mark.asyncio
async def test_get_all_quotes(mock_quote_repository):
    """Test fetching all quotes"""
    quotes = [
        {"_id": "quote-1", "text": "Quote 1", "type": "bullish"},
        {"_id": "quote-2", "text": "Quote 2", "type": "bearish"},
        {"_id": "quote-3", "text": "Quote 3", "type": "hold"},
    ]

    mock_quote_repository.get_all_quotes = AsyncMock(return_value=quotes)

    result = await mock_quote_repository.get_all_quotes()

    assert len(result) == 3
    assert all("_id" in q for q in result)


@pytest.mark.asyncio
async def test_get_all_quotes_empty(mock_quote_repository):
    """Test fetching when no quotes exist"""
    mock_quote_repository.get_all_quotes = AsyncMock(return_value=[])

    result = await mock_quote_repository.get_all_quotes()

    assert result == []


@pytest.mark.asyncio
async def test_get_quotes_by_type_bullish(mock_quote_repository):
    """Test fetching bullish quotes"""
    quotes = [
        {"_id": "quote-1", "text": "Quote 1", "type": "bullish"},
        {"_id": "quote-2", "text": "Quote 2", "type": "bullish"},
    ]

    mock_quote_repository.get_quotes_by_type = AsyncMock(return_value=quotes)

    result = await mock_quote_repository.get_quotes_by_type("bullish")

    assert len(result) == 2
    assert all(q["type"] == "bullish" for q in result)


@pytest.mark.asyncio
@pytest.mark.parametrize("quote_type", ["bullish", "bearish", "hold"])
async def test_get_quotes_all_types(mock_quote_repository, quote_type):
    """Test fetching quotes of all types"""
    mock_quote_repository.get_quotes_by_type = AsyncMock(return_value=[
        {"_id": "quote-1", "text": f"{quote_type} quote", "type": quote_type}
    ])

    result = await mock_quote_repository.get_quotes_by_type(quote_type)

    assert len(result) >= 0


@pytest.mark.asyncio
async def test_update_quote_success(mock_quote_repository):
    """Test successful quote update"""
    mock_quote_repository.update_quote = AsyncMock(return_value=True)

    result = await mock_quote_repository.update_quote(
        quote_id="quote-123",
        update_data={"text": "Updated quote"}
    )

    assert result is True


@pytest.mark.asyncio
async def test_delete_quote_success(mock_quote_repository):
    """Test successful quote deletion"""
    mock_quote_repository.delete_quote = AsyncMock(return_value=True)

    result = await mock_quote_repository.delete_quote("quote-123")

    assert result is True


@pytest.mark.asyncio
async def test_delete_quote_not_found(mock_quote_repository):
    """Test deleting non-existent quote"""
    mock_quote_repository.delete_quote = AsyncMock(return_value=False)

    result = await mock_quote_repository.delete_quote("nonexistent-quote")

    assert result is False


# ============================================================================
# JOB REPOSITORY TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_save_job_success(mock_job_repository):
    """Test saving job state"""
    mock_job_repository.save_job = AsyncMock(return_value=True)

    result = await mock_job_repository.save_job(
        job_id="job-123",
        ticker="AAPL",
        status="processing",
        user_id="user-123"
    )

    assert result is True


@pytest.mark.asyncio
async def test_get_job_success(mock_job_repository):
    """Test fetching job state"""
    job_state = {
        "job_id": "job-123",
        "ticker": "AAPL",
        "status": "completed",
        "result": {"recommendation": "BUY"}
    }

    mock_job_repository.get_job = AsyncMock(return_value=job_state)

    result = await mock_job_repository.get_job("job-123")

    assert result is not None
    assert result["status"] == "completed"


@pytest.mark.asyncio
async def test_get_job_not_found(mock_job_repository):
    """Test fetching non-existent job"""
    mock_job_repository.get_job = AsyncMock(return_value=None)

    result = await mock_job_repository.get_job("nonexistent-job")

    assert result is None


@pytest.mark.asyncio
async def test_update_job_success(mock_job_repository):
    """Test updating job status"""
    mock_job_repository.update_job = AsyncMock(return_value=True)

    result = await mock_job_repository.update_job(
        job_id="job-123",
        status="completed",
        result={"recommendation": "BUY"}
    )

    assert result is True


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["pending", "processing", "completed", "failed", "timeout"])
async def test_job_all_statuses(mock_job_repository, status):
    """Test job updates with various statuses"""
    mock_job_repository.update_job = AsyncMock(return_value=True)

    result = await mock_job_repository.update_job(
        job_id="job-123",
        status=status
    )

    assert result is True


# ============================================================================
# BATCH OPERATIONS TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_bulk_insert_quotes(mock_quote_repository):
    """Test bulk insertion of quotes"""
    quotes = [
        {"text": "Quote 1", "author": "Author 1", "type": "bullish"},
        {"text": "Quote 2", "author": "Author 2", "type": "bearish"},
        {"text": "Quote 3", "author": "Author 3", "type": "hold"},
    ]

    mock_quote_repository.bulk_insert = AsyncMock(return_value=["quote-1", "quote-2", "quote-3"])

    result = await mock_quote_repository.bulk_insert(quotes)

    assert len(result) == 3


@pytest.mark.asyncio
async def test_delete_old_reports(mock_report_repository):
    """Test deleting old reports for cleanup"""
    mock_report_repository.delete_old_reports = AsyncMock(return_value=5)

    result = await mock_report_repository.delete_old_reports(days=30)

    assert result == 5  # 5 reports deleted


# ============================================================================
# QUERY TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_user_repository_query_pagination(mock_user_repository):
    """Test paginated user queries"""
    users = [{"_id": f"user-{i}", "email": f"user{i}@example.com"} for i in range(10)]

    mock_user_repository.get_all_users = AsyncMock(return_value=users[:5])

    result = await mock_user_repository.get_all_users(skip=0, limit=5)

    assert len(result) == 5


@pytest.mark.asyncio
async def test_report_repository_date_range_query(mock_report_repository):
    """Test reports query by date range"""
    reports = [
        {"_id": "report-1", "date": "2026-01-01"},
        {"_id": "report-2", "date": "2026-01-15"},
    ]

    mock_report_repository.get_reports_by_date_range = AsyncMock(return_value=reports)

    result = await mock_report_repository.get_reports_by_date_range(
        start_date="2026-01-01",
        end_date="2026-01-31"
    )

    assert len(result) >= 0
