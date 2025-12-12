from fastapi import APIRouter, HTTPException
from src.models.schemas import EvaluationRequest, EvaluationResult
from src.services.audit_service import AuditService

router = APIRouter()
audit_service = AuditService()

@router.post("/evaluate", response_model=EvaluationResult)
async def evaluate(payload: EvaluationRequest):
    try:
        return await audit_service.evaluate_interaction(payload)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))