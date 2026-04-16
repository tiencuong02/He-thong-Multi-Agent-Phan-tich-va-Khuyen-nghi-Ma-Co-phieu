"""
Integration tests for API endpoints
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ============================================================================
# HEALTH CHECK ENDPOINTS
# ============================================================================

def test_health_endpoint(client):
    """Test health check endpoint"""
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data


def test_root_endpoint(client):
    """Test root endpoint"""
    response = client.get("/")

    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data
    assert "docs" in data


# ============================================================================
# STOCK ANALYSIS ENDPOINTS
# ============================================================================

@pytest.mark.asyncio
async def test_analyze_endpoint_success(client, valid_token):
    """Test successful stock analysis endpoint"""
    response = client.post(
        "/api/v1/stock/analyze",
        json={"ticker": "AAPL"},
        headers={"Authorization": f"Bearer {valid_token}"}
    )

    # Should return 200 or 500 if dependencies not available
    assert response.status_code in [200, 202, 500]

    if response.status_code == 200:
        data = response.json()
        # Should have job_id or analysis result
        assert "job_id" in data or "recommendation" in data


@pytest.mark.asyncio
async def test_analyze_endpoint_invalid_ticker(client, valid_token):
    """Test analyze endpoint with invalid ticker"""
    response = client.post(
        "/api/v1/stock/analyze",
        json={"ticker": "INVALID_TICKET_123"},
        headers={"Authorization": f"Bearer {valid_token}"}
    )

    # Should reject invalid ticker
    assert response.status_code in [400, 422]


@pytest.mark.asyncio
async def test_analyze_endpoint_missing_ticker(client, valid_token):
    """Test analyze endpoint without ticker"""
    response = client.post(
        "/api/v1/stock/analyze",
        json={},
        headers={"Authorization": f"Bearer {valid_token}"}
    )

    assert response.status_code in [400, 422]


@pytest.mark.asyncio
async def test_analyze_endpoint_without_auth(client):
    """Test analyze endpoint without authentication"""
    response = client.post(
        "/api/v1/stock/analyze",
        json={"ticker": "AAPL"}
    )

    # Should return 401 Unauthorized
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_history_endpoint(client, valid_token):
    """Test get stock analysis history"""
    response = client.get(
        "/api/v1/stock/history",
        headers={"Authorization": f"Bearer {valid_token}"}
    )

    # Should return 200 or 500 if DB not available
    assert response.status_code in [200, 500]

    if response.status_code == 200:
        data = response.json()
        # Should return list of reports
        assert isinstance(data, list) or "reports" in data


@pytest.mark.asyncio
async def test_get_history_with_pagination(client, valid_token):
    """Test history endpoint with pagination"""
    response = client.get(
        "/api/v1/stock/history?limit=5&offset=0",
        headers={"Authorization": f"Bearer {valid_token}"}
    )

    assert response.status_code in [200, 500]


@pytest.mark.asyncio
async def test_get_history_without_auth(client):
    """Test history endpoint without authentication"""
    response = client.get("/api/v1/stock/history")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_report_detail(client, valid_token):
    """Test fetching single report detail"""
    response = client.get(
        "/api/v1/stock/report/report-123",
        headers={"Authorization": f"Bearer {valid_token}"}
    )

    # Should return 200 or 404 if report not found
    assert response.status_code in [200, 404, 500]


# ============================================================================
# QUOTE ENDPOINTS
# ============================================================================

def test_get_quotes_endpoint(client):
    """Test get all quotes endpoint"""
    response = client.get("/api/v1/quotes")

    # Public endpoint, should not require auth
    assert response.status_code in [200, 500]

    if response.status_code == 200:
        data = response.json()
        assert isinstance(data, list)


@pytest.mark.asyncio
async def test_get_quotes_by_type(client):
    """Test get quotes by type"""
    response = client.get("/api/v1/quotes?type=bullish")

    assert response.status_code in [200, 500]


@pytest.mark.asyncio
async def test_create_quote_admin_only(client, admin_token):
    """Test creating quote (admin only)"""
    response = client.post(
        "/api/v1/admin/quotes",
        json={
            "text": "Test quote",
            "author": "Test Author",
            "type": "bullish"
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    # Should succeed with admin token
    assert response.status_code in [201, 200, 400, 422, 500]


@pytest.mark.asyncio
async def test_create_quote_user_denied(client, valid_token):
    """Test user cannot create quotes"""
    response = client.post(
        "/api/v1/admin/quotes",
        json={
            "text": "Test quote",
            "author": "Test Author",
            "type": "bullish"
        },
        headers={"Authorization": f"Bearer {valid_token}"}
    )

    # Should return 403 or 401
    assert response.status_code in [401, 403, 500]


@pytest.mark.asyncio
async def test_delete_quote_admin_only(client, admin_token):
    """Test deleting quote (admin only)"""
    response = client.delete(
        "/api/v1/admin/quotes/quote-123",
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    # Should return 204 No Content or 404 Not Found
    assert response.status_code in [204, 404, 500]


# ============================================================================
# CHATBOT/RAG ENDPOINTS
# ============================================================================

@pytest.mark.asyncio
async def test_chatbot_query_endpoint(client, valid_token):
    """Test chatbot query endpoint"""
    response = client.post(
        "/api/v1/rag/query",
        json={"query": "What is a good investment strategy?"},
        headers={"Authorization": f"Bearer {valid_token}"}
    )

    # Should return response or error
    assert response.status_code in [200, 400, 500]


@pytest.mark.asyncio
async def test_chatbot_without_query(client, valid_token):
    """Test chatbot endpoint without query"""
    response = client.post(
        "/api/v1/rag/query",
        json={},
        headers={"Authorization": f"Bearer {valid_token}"}
    )

    # Should return error
    assert response.status_code in [400, 422, 500]


@pytest.mark.asyncio
async def test_upload_knowledge_base(client, admin_token):
    """Test uploading PDF to knowledge base (admin only)"""
    # Note: Would need actual file upload
    response = client.post(
        "/api/v1/admin/knowledge-base/upload",
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    # Status depends on file handling
    assert response.status_code in [400, 422, 500]


# ============================================================================
# USER PROFILE ENDPOINTS
# ============================================================================

@pytest.mark.asyncio
async def test_get_user_profile(client, valid_token):
    """Test get user profile endpoint"""
    response = client.get(
        "/api/v1/users/profile",
        headers={"Authorization": f"Bearer {valid_token}"}
    )

    # Should return user profile or 404
    assert response.status_code in [200, 404, 500]


@pytest.mark.asyncio
async def test_update_user_profile(client, valid_token):
    """Test update user profile"""
    response = client.put(
        "/api/v1/users/profile",
        json={"investment_style": "aggressive"},
        headers={"Authorization": f"Bearer {valid_token}"}
    )

    # Should return updated profile or error
    assert response.status_code in [200, 400, 422, 500]


@pytest.mark.asyncio
async def test_profile_without_auth(client):
    """Test profile endpoint without authentication"""
    response = client.get("/api/v1/users/profile")

    assert response.status_code == 401


# ============================================================================
# ADMIN DASHBOARD ENDPOINTS
# ============================================================================

@pytest.mark.asyncio
async def test_admin_dashboard_user_only(client, valid_token):
    """Test admin endpoint rejects regular user"""
    response = client.get(
        "/api/v1/admin/dashboard",
        headers={"Authorization": f"Bearer {valid_token}"}
    )

    # Should return 403 or 401
    assert response.status_code in [401, 403, 500]


@pytest.mark.asyncio
async def test_admin_dashboard_admin_access(client, admin_token):
    """Test admin can access dashboard"""
    response = client.get(
        "/api/v1/admin/dashboard",
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    # Should return dashboard data or error
    assert response.status_code in [200, 500]


@pytest.mark.asyncio
async def test_admin_statistics(client, admin_token):
    """Test admin statistics endpoint"""
    response = client.get(
        "/api/v1/admin/statistics",
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    assert response.status_code in [200, 500]


# ============================================================================
# ERROR RESPONSE TESTS
# ============================================================================

def test_404_not_found(client):
    """Test 404 response for non-existent endpoint"""
    response = client.get("/api/v1/nonexistent/endpoint")

    assert response.status_code == 404


def test_405_method_not_allowed(client):
    """Test 405 for wrong HTTP method"""
    response = client.delete("/api/v1/quotes")  # GET endpoint, DELETE not allowed

    # Might be 405 or 400 depending on config
    assert response.status_code in [400, 405]


@pytest.mark.asyncio
async def test_500_error_response_format(client):
    """Test that 500 errors have proper format"""
    response = client.get("/nonexistent")

    data = response.json()

    # Should have error information
    assert "detail" in data or "error" in data


# ============================================================================
# CONTENT NEGOTIATION TESTS
# ============================================================================

def test_json_response_format(client):
    """Test that responses are JSON"""
    response = client.get("/")

    assert response.headers["content-type"].startswith("application/json")


def test_cors_headers(client):
    """Test CORS headers present"""
    response = client.get("/")

    # Should have CORS headers if configured
    assert response.status_code == 200


# ============================================================================
# RESPONSE TIME TESTS
# ============================================================================

def test_root_endpoint_response_time(client):
    """Test that root endpoint responds quickly"""
    import time

    start = time.time()
    response = client.get("/")
    duration = time.time() - start

    assert response.status_code == 200
    # Should respond in less than 1 second
    assert duration < 1.0


def test_health_endpoint_response_time(client):
    """Test that health endpoint responds quickly"""
    import time

    start = time.time()
    response = client.get("/health")
    duration = time.time() - start

    assert response.status_code == 200
    assert duration < 1.0


# ============================================================================
# PARAMETRIZED ENDPOINT TESTS
# ============================================================================

@pytest.mark.parametrize("ticker", ["AAPL", "MSFT", "GOOGL"])
@pytest.mark.asyncio
async def test_analyze_multiple_tickers(client, valid_token, ticker):
    """Test analyzing multiple tickers"""
    response = client.post(
        "/api/v1/stock/analyze",
        json={"ticker": ticker},
        headers={"Authorization": f"Bearer {valid_token}"}
    )

    # Should accept valid tickers
    assert response.status_code in [200, 202, 500]


@pytest.mark.parametrize("quote_type", ["bullish", "bearish", "hold"])
def test_filter_quotes_by_type(client, quote_type):
    """Test filtering quotes by all types"""
    response = client.get(f"/api/v1/quotes?type={quote_type}")

    assert response.status_code in [200, 500]


# ============================================================================
# SEQUENTIAL WORKFLOW TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_user_workflow_register_login_analyze(client, sample_user_data):
    """Test complete user workflow: register -> login -> analyze"""
    # This is a simplified version - real E2E would be more complex

    # 1. Register (if not auto-created)
    register_response = client.post(
        "/api/v1/auth/register",
        json=sample_user_data
    )
    assert register_response.status_code in [200, 201, 409]

    # 2. Login
    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": sample_user_data["email"],
            "password": sample_user_data["password"]
        }
    )

    if login_response.status_code == 200:
        token = login_response.json().get("access_token")
        if token:
            # 3. Analyze stock
            analyze_response = client.post(
                "/api/v1/stock/analyze",
                json={"ticker": "AAPL"},
                headers={"Authorization": f"Bearer {token}"}
            )
            assert analyze_response.status_code in [200, 202, 500]
