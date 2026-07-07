from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import chat, telemetry, dispatch, auth
from app.core.logging_config import setup_logging

setup_logging()

app = FastAPI(
    title="Voltaic.AI API",
    description="Intelligent, low-latency multi-agent stadium operations and fan assistance backend for FIFA 2026",
    version="1.0.0"
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "https://voltaic-frontend.vercel.app"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(telemetry.router, prefix="/api/telemetry", tags=["Telemetry"])
app.include_router(dispatch.router, prefix="/api/dispatch", tags=["Dispatch"])

@app.get("/")
async def health_check():
    return {
        "status": "healthy",
        "service": "Voltaic.AI Backend",
        "version": "1.0.0"
    }
