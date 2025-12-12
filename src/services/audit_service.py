from src.models.schemas import EvaluationRequest, EvaluationResult
from src.services.llm_service import GroqClient
from src.utils.metrics import calculate_latency
from src.core.config import settings

class AuditService:
    def __init__(self):
        self.llm_client = GroqClient()

    def _calculate_cost(self, input_toks: int, output_toks: int) -> float:
        """Calculates cost based on Groq/Llama-3 pricing."""
        in_cost = (input_toks / 1000) * settings.INPUT_COST_PER_1K
        out_cost = (output_toks / 1000) * settings.OUTPUT_COST_PER_1K
        return round(in_cost + out_cost, 6)

    def _build_audit_prompt(self, req: EvaluationRequest) -> str:
        # Truncate context to prevent token overflow (Scalability Feature)
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
        1. RELEVANCE & COMPLETENESS: 
           - Does the AI answer the specific question asked? 
           - Is the answer complete? (Score 0 if it ignores key details from context).
        2. FAITHFULNESS (Hallucination Check): 
           - Every claim in the AI response must be supported by the [Retrieval Context]. 
           - If the AI invents a fact (e.g., a price, location, or service) NOT in the text, it is a Hallucination (Score 0).
        
        OUTPUT FORMAT (JSON Only):
        {{
            "relevance_score": <float 0.0-1.0>,
            "faithfulness_score": <float 0.0-1.0>,
            "reasoning": "Concise explanation. Quote the context that supports or contradicts the response."
        }}
        """

    async def evaluate_interaction(self, request: EvaluationRequest) -> EvaluationResult:
        # 1. Metrics
        latency = calculate_latency(request.user_timestamp, request.ai_timestamp)

        # 2. LLM Evaluation
        prompt = self._build_audit_prompt(request)
        llm_data = self.llm_client.get_json_response(prompt)
        content = llm_data["content"]
        
        # 3. Cost Calculation
        cost = self._calculate_cost(llm_data["input_tokens"], llm_data["output_tokens"])

        return EvaluationResult(
            conversation_id=request.conversation_id,
            relevance_score=content.get("relevance_score", 0),
            faithfulness_score=content.get("faithfulness_score", 0),
            latency_seconds=latency,
            estimated_cost_usd=cost,
            reasoning=content.get("reasoning", "Analysis failed.")
        )