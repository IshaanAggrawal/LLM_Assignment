import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict

class EvaluationCache:
    def __init__(self, max_size: int = 10000, ttl_hours: int = 24):
        self._cache: Dict[str, dict] = {}
        self.max_size = max_size
        self.ttl = timedelta(hours=ttl_hours)
    
    def _generate_key(self, query: str, response: str) -> str:
        content = f"{query.strip()}|{response.strip()}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def get(self, query: str, response: str) -> Optional[dict]:
        key = self._generate_key(query, response)
        
        if key in self._cache:
            entry = self._cache[key]
            if datetime.utcnow() - entry["cached_at"] < self.ttl:
                return entry["result"]
            else:
                del self._cache[key]
        return None
    
    def set(self, query: str, response: str, result: dict):
        key = self._generate_key(query, response)
        
        if len(self._cache) >= self.max_size:
            oldest_key = min(self._cache.keys(), 
                           key=lambda k: self._cache[k]["cached_at"])
            del self._cache[oldest_key]
        
        self._cache[key] = {
            "result": result,
            "cached_at": datetime.utcnow()
        }
    
    def stats(self) -> dict:
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "usage_percent": (len(self._cache) / self.max_size) * 100
        }

# Singleton Instance
cache = EvaluationCache()