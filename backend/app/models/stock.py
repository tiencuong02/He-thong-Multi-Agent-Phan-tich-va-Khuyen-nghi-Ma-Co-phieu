from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from app.models.quote import Quote

class AgentTraceStep(BaseModel):
    model_config = {"extra": "allow"}

    agent: str
    status: str
    tools: Optional[List[str]] = None
    logic: Optional[str] = None
    data: Optional[str] = None
    fallback: Optional[bool] = None
    sentiment: Optional[str] = None
    overall_assessment: Optional[str] = None

class AnalysisResult(BaseModel):
    ticker: str
    recommendation: str
    price: float
    trend: str
    confidence: float
    risk_opportunity: str
    
    # New Professional Metrics
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    investment_strategy: Optional[str] = None

    # Sentiment fields (from AlphaVantage news)
    sentiment_score: Optional[float] = None
    sentiment_label: Optional[str] = None      # Tích cực / Tiêu cực / Trung lập
    news_count: Optional[int] = None
    ai_rationale: Optional[str] = None         # LLM-generated Vietnamese report
    overall_assessment: Optional[str] = None   # Tích cực / Tiêu cực / Trung lập
    price_history: Optional[List[Dict[str, Any]]] = None  # [{date, open, high, low, close, volume}] ascending

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
