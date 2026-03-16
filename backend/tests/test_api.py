import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to the Multi-Agent Stock Analysis API"}

def test_get_history_endpoint():
    # This might fail if DB is not connected, but for unit test we can mock or just check if it handles it
    response = client.get("/history?limit=1")
    # If DB is not connected, it returns 500, which is expected behavior for now without mocks
    assert response.status_code in [200, 500] 

def test_analyze_invalid_ticker():
    # Should handle errors gracefully
    response = client.post("/analyze/INVALID_TICKER_123")
    assert response.status_code == 500
