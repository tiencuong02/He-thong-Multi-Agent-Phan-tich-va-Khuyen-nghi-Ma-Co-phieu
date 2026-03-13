from pydantic import BaseModel
from typing import Optional

class AnalysisRequest(BaseModel):
    ticker: str

class AnalysisResult(BaseModel):
    ticker: str
    recommendation: str
    report: str
    sentiment: str
