from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from app.models.quote import Quote

class AgentTraceStep(BaseModel):
    agent: str
    status: str
    tools: Optional[List[str]] = None
    logic: Optional[str] = None

class AnalysisResult(BaseModel):
    ticker: str
    recommendation: str
    price: float
    trend: str
    confidence: float
    risk_opportunity: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    user_id: Optional[str] = None
    agent_trace: Optional[List[AgentTraceStep]] = None
    quote: Optional[Quote] = None

class JobState(BaseModel):
    job_id: str
    status: str # pending, processing, completed, failed
    ticker: str
    result: Optional[AnalysisResult] = None
    error: Optional[str] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class AnalysisRequest(BaseModel):
    ticker: str

class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    result: Optional[AnalysisResult] = None
    error: Optional[str] = None
