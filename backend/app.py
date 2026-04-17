import os
import sys

# Ensure 'backend' directory is in sys.path for absolute imports to work correctly
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from routes import chat
from services.database import db
from contextlib import asynccontextmanager
from starlette.responses import JSONResponse
from utils.resilience import fallback_string

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Connect to DB
    await db.connect()
    yield
    # Shutdown: Close connection
    await db.close()

app = FastAPI(
    title="NPGC Assistant API (MySQL)",
    description="A modular chatbot backend with AI, FAQ, Redis, and MySQL support.",
    version="2.0.0",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development, allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Exception Handler for "Safe Mode" / UX Fallback
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    print(f"Global Crash Captured: {exc}")
    return JSONResponse(
        status_code=200,
        content={
            "response": "I'm currently experiencing high traffic. Please try asking about Admissions or Courses!",
            "source": "global_error_handler",
            "language": "en-US",
            "suggestions": ["What courses are available?", "How do I apply?", "Tell me about faculty"]
        }
    )

# Include Routers
app.include_router(chat.router, prefix="/api", tags=["Chat"])

# Serve frontend static files
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")
FRONTEND_DIR = os.path.abspath(FRONTEND_DIR)

@app.get("/", include_in_schema=False)
async def serve_frontend():
    """Serve the frontend index.html"""
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

@app.get("/health")
async def health():
    return {"message": "Welcome to the NPGC Assistant | Modular FastAPI Chatbot API", "status": "online"}

@app.get("/api/debug-check")
async def debug_check():
    """Diagnostic route to check connections in production."""
    db_status = "Online ✅" if db.pool else "Offline ❌"
    
    # Check keys (masked for safety)
    gemini_key = os.getenv("GEMINI_API_KEY")
    groq_key = os.getenv("GROQ_API_KEY")
    
    return {
        "database": db_status,
        "database_host": os.getenv("MYSQL_HOST", "Not Set"),
        "gemini_api_key": "Set ✅" if gemini_key else "Not Set ❌",
        "groq_api_key": "Set ✅" if groq_key else "Not Set ❌",
        "env_port": os.getenv("PORT", "Default (7860)"),
        "tip": "If Database is Offline, ensure Aiven Whitelist includes 0.0.0.0/0"
    }

# Mount frontend static files at root - must come AFTER all API routes
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    # Hugging Face Spaces provides the port via the PORT environment variable (default 7860)
    port = int(os.getenv("PORT", 7860))
    uvicorn.run(app, host="0.0.0.0", port=port)

