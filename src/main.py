from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from src.core.config import settings
from src.routes import eval_routes

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In prod, replace with ["http://localhost:3000"]
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(eval_routes.router, prefix="/api/v1")

@app.get("/")
@limiter.limit("5/minute")
def read_root(request: Request):
    return {"message": "Secure Evaluator Running"}

@app.get("/health")
def health_check():
    return {"status": "active", "env": settings.ENV}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)