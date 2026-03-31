from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

class QuoteContext(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"

class QuoteBase(BaseModel):
    content: str
    author: str
    context: QuoteContext = QuoteContext.HOLD

class QuoteCreate(QuoteBase):
    pass

class QuoteUpdate(BaseModel):
    content: Optional[str] = None
    author: Optional[str] = None
    context: Optional[QuoteContext] = None

class Quote(QuoteBase):
    id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class QuoteLog(BaseModel):
    user_id: str
    quote_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    context: QuoteContext
