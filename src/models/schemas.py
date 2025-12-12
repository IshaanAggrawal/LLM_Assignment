from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import datetime

class EvaluationRequest(BaseModel):
    conversation_id: int
    user_query: str
    ai_response: str
    context_texts: List[str]
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

# --- NEW: Add this for Link Support ---
class BatchLinkRequest(BaseModel):
    chat_url: str
    vector_url: str