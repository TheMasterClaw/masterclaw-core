"""Main FastAPI application for MasterClaw Core"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .config import settings
from .models import (
    ChatRequest,
    ChatResponse,
    MemoryEntry,
    MemorySearchRequest,
    MemorySearchResponse,
    HealthResponse,
)
from .llm import router as llm_router
from .memory import get_memory_store, MemoryStore


# Global memory store
memory: MemoryStore = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    global memory
    
    # Startup
    print(f"🐾 MasterClaw Core v{__version__} starting...")
    memory = get_memory_store()
    print(f"✅ Memory store initialized ({settings.MEMORY_BACKEND})")
    print(f"✅ LLM providers: {llm_router.list_providers()}")
    
    yield
    
    # Shutdown
    print("🛑 MasterClaw Core shutting down...")


# Create FastAPI app
app = FastAPI(
    title="MasterClaw Core",
    description="The AI brain behind MasterClaw",
    version=__version__,
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["root"])
async def root():
    """Root endpoint"""
    return {
        "name": "MasterClaw Core",
        "version": __version__,
        "status": "running",
        "endpoints": [
            "/health",
            "/v1/chat",
            "/v1/memory/search",
            "/v1/memory/add",
        ],
    }


@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check():
    """Health check endpoint"""
    services = {
        "memory": settings.MEMORY_BACKEND,
        "llm_providers": llm_router.list_providers(),
    }
    
    return HealthResponse(
        status="healthy",
        version=__version__,
        services=services,
    )


@app.post("/v1/chat", response_model=ChatResponse, tags=["chat"])
async def chat(request: ChatRequest):
    """
    Send a chat message and get an AI response.
    
    Retrieves relevant memories if use_memory is True.
    """
    try:
        # Retrieve memories if enabled
        memories = []
        memories_used = 0
        
        if request.use_memory and request.session_id:
            memories = await memory.search(
                query=request.message,
                top_k=5,
                filter_metadata={"session_id": request.session_id},
            )
            memories_used = len(memories)
        
        # Build system prompt with memories
        system_prompt = request.system_prompt or (
            "You are MasterClaw, an AI familiar bound to Rex deus. "
            "Be helpful, direct, and slightly mischievous when appropriate."
        )
        
        if memories:
            memory_context = "\n\nRelevant context from memory:\n" + "\n".join(
                f"- {m.content}" for m in memories
            )
            system_prompt += memory_context
        
        # Route to LLM
        result = await llm_router.chat(
            message=request.message,
            provider=request.provider,
            model=request.model,
            system_prompt=system_prompt,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
        
        # Store this interaction in memory
        if request.session_id:
            await memory.add(
                content=f"User: {request.message}\nAssistant: {result['response']}",
                metadata={
                    "session_id": request.session_id,
                    "type": "chat_interaction",
                    "model": result["model"],
                },
                source="chat",
            )
        
        return ChatResponse(
            response=result["response"],
            model=result["model"],
            provider=result["provider"],
            session_id=request.session_id,
            tokens_used=result.get("tokens_used"),
            memories_used=memories_used,
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat error: {str(e)}",
        )


@app.post("/v1/memory/search", response_model=MemorySearchResponse, tags=["memory"])
async def search_memory(request: MemorySearchRequest):
    """Search for memories using semantic similarity"""
    try:
        results = await memory.search(
            query=request.query,
            top_k=request.top_k,
            filter_metadata=request.filter_metadata,
        )
        
        return MemorySearchResponse(
            query=request.query,
            results=results,
            total_results=len(results),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search error: {str(e)}",
        )


@app.post("/v1/memory/add", response_model=dict, tags=["memory"])
async def add_memory(entry: MemoryEntry):
    """Add a new memory entry"""
    try:
        memory_id = await memory.add(
            content=entry.content,
            metadata=entry.metadata,
            source=entry.source,
        )
        
        return {
            "success": True,
            "memory_id": memory_id,
            "message": "Memory added successfully",
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Add error: {str(e)}",
        )


@app.get("/v1/memory/{memory_id}", response_model=MemoryEntry, tags=["memory"])
async def get_memory(memory_id: str):
    """Get a specific memory by ID"""
    result = await memory.get(memory_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Memory not found",
        )
    return result


@app.delete("/v1/memory/{memory_id}", response_model=dict, tags=["memory"])
async def delete_memory(memory_id: str):
    """Delete a memory by ID"""
    success = await memory.delete(memory_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Memory not found",
        )
    return {
        "success": True,
        "message": "Memory deleted successfully",
    }
