from fastapi import FastAPI
from src.core.config import settings
from src.routes import eval_routes

app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION)
app.include_router(eval_routes.router, prefix="/api/v1")
@app.get("/")
def read_root():
    return {
        "message": "beyondEval api working",
        "status": "Running",
        "documentation": "/docs",  
        "health_check": "/health"
    }

@app.get("/health")
def health_check():
    return {"status": "active", "env": settings.ENV}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)