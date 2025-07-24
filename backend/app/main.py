# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.api import chat  # Import the chat router
from dotenv import load_dotenv
import asyncio

load_dotenv()

# Global graph cache to avoid recompilation
_graph_cache = None
_graph_lock = asyncio.Lock()

async def get_cached_graph():
    """Get or create cached graph instance - thread-safe singleton"""
    global _graph_cache
    async with _graph_lock:
        if _graph_cache is None:
            from agents.sql_with_preprocess.main import create_graph
            print("🔄 Creating and caching graph instance...")
            _graph_cache = await create_graph()
            print("✅ Graph cached successfully")
        return _graph_cache

app = FastAPI(
    title="LangGraph Backend",
    description="Backend API for interacting with a LangGraph",
    version="0.1.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://csql-agent.vercel.app"],  # CORS origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(chat.router, prefix="/api") # Mount the chat router under /api

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)