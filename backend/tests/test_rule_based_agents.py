import pytest
import asyncio
from app.agents.financial_analyst import analyze_financials
from app.agents.investment_advisor import get_recommendation

def test_analyze_financials_bullish():
    data = {
        "symbol": "FPT",
        "prices": [
            {"close": 110, "volume": 2000}, # current (newest)
            {"close": 105, "volume": 1000}, # prev
        ] + [{"close": 100, "volume": 1000}] * 18 # 20 total
    }
    analysis = analyze_financials(data)
    assert analysis["trend"] == "up"
    assert analysis["ma5"] > analysis["ma20"]
    assert analysis["volume_change"] > 0

def test_analyze_financials_bearish():
    data = {
        "symbol": "FPT",
        "prices": [
            {"close": 90, "volume": 500}, # current
            {"close": 95, "volume": 1000}, # prev
        ] + [{"close": 100, "volume": 1000}] * 18
    }
    analysis = analyze_financials(data)
    assert analysis["trend"] == "down"
    assert analysis["ma5"] < analysis["ma20"]

def test_recommendation_buy():
    analysis = {
        "symbol": "FPT",
        "price": 110,
        "ma5": 105,
        "ma20": 100,
        "trend": "up",
        "volume_change": 0.5
    }
    rec = get_recommendation(analysis)
    assert rec["recommendation"] == "BUY"
    assert rec["confidence"] > 0.8

def test_recommendation_sell():
    analysis = {
        "symbol": "FPT",
        "price": 90,
        "ma5": 95,
        "ma20": 100,
        "trend": "down",
        "volume_change": -0.2
    }
    rec = get_recommendation(analysis)
    assert rec["recommendation"] == "SELL"
    assert rec["confidence"] > 0.7

def test_recommendation_hold():
    analysis = {
        "symbol": "FPT",
        "price": 100,
        "ma5": 100,
        "ma20": 100,
        "trend": "down", # ma5 not > ma20
        "volume_change": 0
    }
    rec = get_recommendation(analysis)
    assert rec["recommendation"] == "HOLD"

if __name__ == "__main__":
    print("Running tests manually...")
    test_analyze_financials_bullish()
    test_analyze_financials_bearish()
    test_recommendation_buy()
    test_recommendation_sell()
    test_recommendation_hold()
    print("All manual tests passed!")
