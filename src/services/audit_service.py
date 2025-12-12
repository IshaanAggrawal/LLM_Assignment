from src.models.schemas import EvaluationRequest, EvaluationResult
from src.services.llm_service import GroqClient
from src.utils.metrics import calculate_latency
from src.core.config import settings

class AuditService:
    def __init__(self):
        self.llm_client = GroqClient()

    def _calculate_cost(self, input_toks: int, output_toks: int) -> float:
        in_cost = (input_toks / 1000) * settings.INPUT_COST_PER_1K
        out_cost = (output_toks / 1000) * settings.OUTPUT_COST_PER_1K
        return round(in_cost + out_cost, 6)

    def _build_react_prompt(self, req: EvaluationRequest) -> str:
        # Truncate context to prevent token overflow (Security Guardrail)
        safe_context = [txt[:2000] for txt in req.context_texts[:5]] 
        context_block = "\n".join([f"- {txt}" for txt in safe_context])
        
        return f"""
        ROLE: Expert Legal Auditor.
        TASK: Assess 'AI Response' reliability against 'Ground Truth Context'.
        
        DATA:
        [Query]: "{req.user_query}"
        [Response]: "{req.ai_response}"
        [Context]:
        {context_block}
        
        METHODOLOGY (Chain of Thought):
        1. Extract all factual claims from [Response].
        2. Verify each claim against [Context].
        3. If a claim is missing from Context, Faithfulness = 0.
        4. If Response ignores Query, Relevance = 0.
        
        OUTPUT JSON:
        {{
            "relevance_score": <float 0.0-1.0>,
            "faithfulness_score": <float 0.0-1.0>,
            "reasoning": "<Concise verification steps>"
        }}
        """

    async def evaluate_interaction(self, request: EvaluationRequest) -> EvaluationResult:
        # 1. Metrics
        latency = calculate_latency(request.user_timestamp, request.ai_timestamp)

        # 2. LLM Evaluation
        prompt = self._build_react_prompt(request)
        llm_data = self.llm_client.get_json_response(prompt)
        
        # 3. Cost Calculation
        cost = self._calculate_cost(llm_data["input_tokens"], llm_data["output_tokens"])
        content = llm_data["content"]

        # 4. Result Construction
        return EvaluationResult(
            conversation_id=request.conversation_id,
            relevance_score=content.get("relevance_score", 0),
            faithfulness_score=content.get("faithfulness_score", 0),
            latency_seconds=latency,
            estimated_cost_usd=cost,
            reasoning=content.get("reasoning", "Analysis failed.")
        )