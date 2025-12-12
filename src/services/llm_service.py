import json
from groq import Groq
from tenacity import retry, stop_after_attempt, wait_exponential
from src.core.config import settings

client = Groq(api_key=settings.GROQ_API_KEY)

class GroqClient:
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def get_json_response(self, prompt: str) -> dict:
        try:
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "You are a strict QA Auditor. Output ONLY valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                response_format={"type": "json_object"}
            )
            
            content = json.loads(completion.choices[0].message.content)
            
            usage = completion.usage
            return {
                "content": content,
                "input_tokens": usage.prompt_tokens,
                "output_tokens": usage.completion_tokens
            }
        except Exception as e:
            print(f"Groq API Error: {e}")
            raise e