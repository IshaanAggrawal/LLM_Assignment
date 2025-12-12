import json
import httpx
from fastapi import APIRouter, HTTPException, UploadFile, File, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from src.models.schemas import EvaluationRequest, EvaluationResult, BatchLinkRequest
from src.services.audit_service import AuditService

# Initialize Router (No API Key Dependency)
router = APIRouter()

audit_service = AuditService()
limiter = Limiter(key_func=get_remote_address)

# --- Helper: Universal Parser ---
def extract_context_and_turn(chat_data, vector_data, target_turn):
    try:
        # 1. Extract Context
        if 'data' in vector_data and 'vector_data' in vector_data['data']:
            vector_items = vector_data['data']['vector_data']
        else:
            vector_items = vector_data.get('vector_data', [])
        
        context_texts = [item.get('text', '') for item in vector_items]

        # 2. Extract Turn
        turns = chat_data.get('chat_conversation', {}).get('conversation_turns', chat_data.get('conversation_turns', []))
        
        for i, turn in enumerate(turns):
            if turn['turn'] == target_turn and turn['role'] == 'AI/Chatbot':
                user_turn = turns[i-1]
                return EvaluationRequest(
                    conversation_id=chat_data.get('chat_id', 0),
                    user_query=user_turn['message'],
                    ai_response=turn['message'],
                    context_texts=context_texts,
                    user_timestamp=user_turn['created_at'],
                    ai_timestamp=turn['created_at']
                )
        return None
    except Exception as e:
        print(f"Parsing Error: {e}")
        return None

# --- Route 1: Standard Evaluation ---
@router.post("/evaluate", response_model=EvaluationResult)
@limiter.limit("10/minute") # Rate Limit Kept
async def evaluate(request: Request, payload: EvaluationRequest):
    try:
        return await audit_service.evaluate_interaction(payload)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Route 2: File Upload (Batch) ---
@router.post("/evaluate/batch")
@limiter.limit("5/minute") # Rate Limit Kept
async def evaluate_batch_file(request: Request, chat_file: UploadFile = File(...), vector_file: UploadFile = File(...)):
    try:
        chat_content = await chat_file.read()
        vector_content = await vector_file.read()
        
        # Default to turn 14 if using file upload (or you can add logic to extract from filename)
        req_payload = extract_context_and_turn(json.loads(chat_content), json.loads(vector_content), target_turn=14)
        
        if not req_payload:
            return {"error": "Target turn 14 not found."}
            
        return await audit_service.evaluate_interaction(req_payload)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Route 3: URL Evaluation (Links) ---
@router.post("/evaluate/batch-url")
@limiter.limit("5/minute") # Rate Limit Kept
async def evaluate_batch_url(request: Request, payload: BatchLinkRequest):
    async with httpx.AsyncClient(follow_redirects=True) as client:
        try:
            chat_resp = await client.get(payload.chat_url)
            vector_resp = await client.get(payload.vector_url)
            
            req_payload = extract_context_and_turn(
                chat_resp.json(), 
                vector_resp.json(), 
                target_turn=payload.target_turn
            )

            if not req_payload:
                raise HTTPException(status_code=404, detail="Target turn not found.")

            return await audit_service.evaluate_interaction(req_payload)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))