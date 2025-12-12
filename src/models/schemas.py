from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import datetime

class EvaluationRequest(BaseModel):
    conversation_id: int
    user_query: str = Field(..., max_length=10000) 
    ai_response: str = Field(..., max_length=20000)
    context_texts: List[str] = Field(..., max_items=50)
    
    user_timestamp: Optional[str] = None
    ai_timestamp: Optional[str] = None

    @validator('ai_response')
    def validate_response(cls, v):
        if not v or not v.strip():
            raise ValueError("AI Response cannot be empty")
        return v
class EvaluationResult(BaseModel):
    conversation_id: int
    relevance_score: float = Field(..., ge=0, le=1)
    faithfulness_score: float = Field(..., ge=0, le=1)
    latency_seconds: float
    estimated_cost_usd: float
    reasoning: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class BatchLinkRequest(BaseModel):
    chat_url: str
    vector_url: str
    target_turn: int = 14