import json
import httpx
from fastapi import APIRouter, HTTPException, UploadFile, File
from src.models.schemas import EvaluationRequest, EvaluationResult, BatchLinkRequest
from src.services.audit_service import AuditService

router = APIRouter()
audit_service = AuditService()

# --- Helper: Universal Parser ---
def extract_context_and_turn(chat_data, vector_data, target_turn=14):
    """Helper to parse JSON and find the target turn (Turn 14)."""
    # 1. Extract Context Text
    if 'data' in vector_data and 'vector_data' in vector_data['data']:
        vector_items = vector_data['data']['vector_data']
    else:
        vector_items = vector_data.get('vector_data', [])
    
    context_texts = [item['text'] for item in vector_items]

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

# --- Route 1: Single Evaluation ---
@router.post("/evaluate", response_model=EvaluationResult)
async def evaluate(payload: EvaluationRequest):
    try:
        return await audit_service.evaluate_interaction(payload)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Route 2: File Upload (Batch) ---
@router.post("/evaluate/batch")
async def evaluate_batch_file(chat_file: UploadFile = File(...), vector_file: UploadFile = File(...)):
    try:
        chat_content = await chat_file.read()
        vector_content = await vector_file.read()
        
        req_payload = extract_context_and_turn(json.loads(chat_content), json.loads(vector_content))
        
        if not req_payload:
            return {"error": "Target turn 14 not found in uploaded files."}
            
        return await audit_service.evaluate_interaction(req_payload)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Route 3: URL Evaluation (Links) ---
@router.post("/evaluate/batch-url")
async def evaluate_batch_url(payload: BatchLinkRequest):
    async with httpx.AsyncClient(follow_redirects=True) as client:
        try:
            # Fetch files from the provided URLs
            chat_resp = await client.get(payload.chat_url)
            vector_resp = await client.get(payload.vector_url)
            
            # Parse and Evaluate
            req_payload = extract_context_and_turn(chat_resp.json(), vector_resp.json())

            if not req_payload:
                raise HTTPException(status_code=404, detail="Target turn not found in linked files.")

            return await audit_service.evaluate_interaction(req_payload)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Link Error: {str(e)}")