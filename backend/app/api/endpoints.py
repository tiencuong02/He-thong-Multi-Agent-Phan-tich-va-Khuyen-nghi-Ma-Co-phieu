from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
import datetime

from app.db.mongodb import get_db
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
    try:
        # Run the crew analysis
        # Note: This is a synchronous blocking call inside an async route.
        # In production, consider running this in a dedicated ThreadPool or as a background task.
        result_dict = run_analysis(ticker)
        
        # Prepare document for MongoDB
        report = {
            "ticker": ticker,
            "risk_opportunity": result_dict.get("risk_opportunity", ""),
            "recommendation": result_dict.get("recommendation", ""),
            "created_at": datetime.datetime.utcnow().isoformat()
        }
        
        db = get_db()
        if db is not None:
             await db["reports"].insert_one(report.copy())
             
        report.pop("_id", None)
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
