import time
from src.models.schemas import EvaluationRequest, EvaluationResult
from src.services.llm_service import GroqClient
from src.utils.metrics import calculate_latency
from src.core.config import settings
from src.services.cache_service import cache 

class AuditService:
    def __init__(self):
        self.llm_client = GroqClient()

    def _calculate_cost(self, input_toks: int, output_toks: int) -> float:
        in_cost = (input_toks / 1000) * settings.INPUT_COST_PER_1K
        out_cost = (output_toks / 1000) * settings.OUTPUT_COST_PER_1K
        return round(in_cost + out_cost, 6)

    def _build_audit_prompt(self, req: EvaluationRequest) -> str:
        safe_context = [txt[:2000] for txt in req.context_texts[:5]] 
        context_block = "\n".join([f"[{i+1}] {txt}" for i, txt in enumerate(safe_context)])
        
        return f"""
        ROLE: Strict Compliance Auditor for a Medical/Legal Chatbot.
        
        INPUT DATA:
        [User Query]: "{req.user_query}"
        [AI Response]: "{req.ai_response}"
        [Retrieval Context]:
        {context_block}
        
        EVALUATION CRITERIA:
        1. RELEVANCE: Does it answer the specific question?
        2. FAITHFULNESS: Is every claim supported by context?
        
        OUTPUT FORMAT (JSON Only):
        {{
            "relevance_score": <float 0.0-1.0>,
            "faithfulness_score": <float 0.0-1.0>,
            "reasoning": "Concise explanation."
        }}
        """

    async def evaluate_interaction(self, request: EvaluationRequest) -> EvaluationResult:
        start_time = time.perf_counter()
        chat_latency = calculate_latency(request.user_timestamp, request.ai_timestamp)
        
        # --- LAYER 0: CACHE CHECK (Zero Cost) ---
        cached_data = cache.get(request.user_query, request.ai_response)
        
        if cached_data:
            end_time = time.perf_counter()
            print("Cache Hit! Skipping LLM.")
            
            # We reconstruct the result using the *Cached Scores* # but the *Current Context* (like conversation_id and execution time)
            return EvaluationResult(
                conversation_id=request.conversation_id,
                relevance_score=cached_data["relevance_score"],
                faithfulness_score=cached_data["faithfulness_score"],
                chat_latency_seconds=chat_latency,
                eval_execution_seconds=round(end_time - start_time, 4),
                estimated_cost_usd=0.0, 
                reasoning=cached_data["reasoning"],
                evaluator_model="Cache-Hit" 
            )

        # --- LAYER 1: DETERMINISTIC GUARDRAILS ---
        if len(request.ai_response.strip()) < 5:
            end_time = time.perf_counter()
            return EvaluationResult(
                conversation_id=request.conversation_id,
                relevance_score=0.0,
                faithfulness_score=0.0,
                chat_latency_seconds=chat_latency,
                eval_execution_seconds=round(end_time - start_time, 4),
                estimated_cost_usd=0.0,
                reasoning="Layer 1 Violation: Response too short/empty.",
                evaluator_model="Deterministic-Check"
            )

        # --- LAYER 2: THE SCOUT (Llama-8B) ---
        prompt = self._build_audit_prompt(request)
        current_model = settings.MODEL_TIER_1 
        
        llm_data = self.llm_client.get_json_response(prompt, model_id=current_model)
        content = llm_data["content"]
        
        relevance = content.get("relevance_score", 0)
        faithfulness = content.get("faithfulness_score", 0)
        
        # --- LAYER 3: THE JUDGE (Llama-70B) ---
        if relevance < 0.9 or faithfulness < 0.9:
            print(f"⚠️ Layer 2 ({current_model}) Unsure. Escalating to Layer 3...")
            current_model = settings.MODEL_TIER_3 
            llm_data_l3 = self.llm_client.get_json_response(prompt, model_id=current_model)
            
            content = llm_data_l3["content"]
            relevance = content.get("relevance_score", 0)
            faithfulness = content.get("faithfulness_score", 0)
            
            total_input = llm_data["input_tokens"] + llm_data_l3["input_tokens"]
            total_output = llm_data["output_tokens"] + llm_data_l3["output_tokens"]
        else:
            total_input = llm_data["input_tokens"]
            total_output = llm_data["output_tokens"]

        end_time = time.perf_counter()
        execution_time = round(end_time - start_time, 4)
        cost = self._calculate_cost(total_input, total_output)

        result_obj = EvaluationResult(
            conversation_id=request.conversation_id,
            relevance_score=relevance,
            faithfulness_score=faithfulness,
            chat_latency_seconds=chat_latency,
            eval_execution_seconds=execution_time,
            estimated_cost_usd=cost,
            reasoning=content.get("reasoning", "Analysis failed.") + f" [Final Decision: {current_model}]",
            evaluator_model=current_model
        )

        cache.set(request.user_query, request.ai_response, result_obj.dict())
        
        return result_obj
