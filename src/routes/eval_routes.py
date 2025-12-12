import json
import httpx
from fastapi import APIRouter, HTTPException, UploadFile, File, Request, BackgroundTasks
from slowapi import Limiter
from slowapi.util import get_remote_address
from src.models.schemas import EvaluationRequest, EvaluationResult, BatchLinkRequest
from src.services.audit_service import AuditService

router = APIRouter()
audit_service = AuditService()
limiter = Limiter(key_func=get_remote_address)

# --- HELPER FUNCTION (Restored) ---
def extract_context_and_turn(chat_data, vector_data, target_turn):
    try:
        if 'data' in vector_data and 'vector_data' in vector_data['data']:
            vector_items = vector_data['data']['vector_data']
        else:
            vector_items = vector_data.get('vector_data', [])
        
        context_texts = [item.get('text', '') for item in vector_items]

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

# --- ORIGINAL ROUTES (Restored for test.py) ---

@router.post("/evaluate", response_model=EvaluationResult)
@limiter.limit("10/minute") 
async def evaluate(request: Request, payload: EvaluationRequest):
    try:
        return await audit_service.evaluate_interaction(payload)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/evaluate/batch")
@limiter.limit("5/minute")
async def evaluate_batch_file(request: Request, chat_file: UploadFile = File(...), vector_file: UploadFile = File(...)):
    try:
        chat_content = await chat_file.read()
        vector_content = await vector_file.read()
        
        req_payload = extract_context_and_turn(json.loads(chat_content), json.loads(vector_content), target_turn=14)
        
        if not req_payload:
            return {"error": "Target turn 14 not found."}
            
        return await audit_service.evaluate_interaction(req_payload)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/evaluate/batch-url")
@limiter.limit("5/minute")
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

# --- NEW INDUSTRY STANDARD ROUTE (Async) ---

async def persist_evaluation(payload: EvaluationRequest):
    # This runs in the background!
    result = await audit_service.evaluate_interaction(payload)
    print(f"✅ [Background Audit] Chat {payload.conversation_id} Score: {result.faithfulness_score} (Latency: {result.eval_execution_seconds}s)")
    # TODO: db.save(result)

@router.post("/evaluate/stream")
async def stream_evaluation(
    request: Request, 
    payload: EvaluationRequest, 
    background_tasks: BackgroundTasks
):
    """
    Industry Pattern: Asynchronous 'Fire-and-Forget'.
    Returns 202 Accepted immediately so the Chatbot UI doesn't hang.
    """
    background_tasks.add_task(persist_evaluation, payload)
    
    return {
        "status": "queued",
        "message": "Evaluation running in background",
        "conversation_id": payload.conversation_id
    }