from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
import datetime
import json

from app.db.mongodb import get_db
from app.db.redis import get_redis
from app.agents.crew import run_analysis

router = APIRouter()

class AnalysisResponse(BaseModel):
    ticker: str
    risk_opportunity: str
    recommendation: str
    created_at: str

@router.post("/analyze/{ticker}", response_model=AnalysisResponse)
async def analyze_stock(ticker: str):
    ticker = ticker.upper()
    redis = get_redis()
    
    # 1. Check Redis Cache
    if redis:
        try:
            cached_data = await redis.get(f"analysis:{ticker}")
            if cached_data:
                print(f"Returning cached data for {ticker}")
                return json.loads(cached_data)
        except Exception as e:
            print(f"Redis error: {e}")

    try:
        # 2. Run the crew analysis (blocking call, consider background task for production)
        result_dict = run_analysis(ticker)
        
        # Prepare document
        report = {
            "ticker": ticker,
            "risk_opportunity": result_dict.get("risk_opportunity", ""),
            "recommendation": result_dict.get("recommendation", ""),
            "created_at": datetime.datetime.utcnow().isoformat()
        }
        
        # 3. Save to MongoDB
        db = get_db()
        if db is not None:
             await db["reports"].insert_one(report.copy())
             
        report.pop("_id", None)
        
        # 4. Save to Redis Cache (TTL 1 hour)
        if redis:
            try:
                await redis.setex(f"analysis:{ticker}", 3600, json.dumps(report))
            except Exception as e:
                print(f"Redis save error: {e}")

        return report
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@router.get("/history", response_model=List[AnalysisResponse])
async def get_history(limit: int = 10):
    try:
        db = get_db()
        if db is None:
            raise HTTPException(status_code=500, detail="Database not connected")
            
        cursor = db["reports"].find().sort("created_at", -1).limit(limit)
        reports = await cursor.to_list(length=limit)
        
        # Clean up ObjectIds for Pydantic serialization
        for r in reports:
            r["_id"] = str(r["_id"])
            
        return reports
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
