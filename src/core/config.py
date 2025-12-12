import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME: str = "ClauseSense Evaluator"
    VERSION: str = "1.0.0"
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY")
    ENV: str = os.getenv("ENV", "development")
    
    # Cost Constants (Llama-3.1-8B)
    INPUT_COST_PER_1K: float = 0.00005
    OUTPUT_COST_PER_1K: float = 0.00008

    @classmethod
    def validate(cls):
        if not cls.GROQ_API_KEY:
            raise ValueError("CRITICAL: Missing GROQ_API_KEY in environment.")

settings = Settings()
settings.validate()