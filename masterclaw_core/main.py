"""Main FastAPI application for MasterClaw Core"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status, WebSocket, WebSocketDisconnect
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
    AnalyticsStatsRequest,
    AnalyticsStatsResponse,
    AnalyticsSummaryResponse,
)
import time

from .analytics import analytics
from .llm import router as llm_router
from .memory import get_memory_store, MemoryStore
from .websocket import manager


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
            "/v1/chat/stream/{session_id} (WebSocket)",
            "/v1/memory/search",
            "/v1/memory/add",
            "/v1/analytics",
            "/v1/analytics/stats",
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
    start_time = time.time()
    status_code = 200
    
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
        
        # Track analytics
        duration_ms = (time.time() - start_time) * 1000
        analytics.track_request("/v1/chat", duration_ms, 200)
        analytics.track_chat(
            provider=result["provider"],
            model=result["model"],
            tokens_used=result.get("tokens_used", 0),
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
        status_code = 400
        duration_ms = (time.time() - start_time) * 1000
        analytics.track_request("/v1/chat", duration_ms, status_code)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        status_code = 500
        duration_ms = (time.time() - start_time) * 1000
        analytics.track_request("/v1/chat", duration_ms, status_code)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat error: {str(e)}",
        )


@app.post("/v1/memory/search", response_model=MemorySearchResponse, tags=["memory"])
async def search_memory(request: MemorySearchRequest):
    """Search for memories using semantic similarity"""
    start_time = time.time()
    
    try:
        results = await memory.search(
            query=request.query,
            top_k=request.top_k,
            filter_metadata=request.filter_metadata,
        )
        
        # Track analytics
        duration_ms = (time.time() - start_time) * 1000
        analytics.track_request("/v1/memory/search", duration_ms, 200)
        analytics.track_memory_search(len(results), duration_ms)
        
        return MemorySearchResponse(
            query=request.query,
            results=results,
            total_results=len(results),
        )
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        analytics.track_request("/v1/memory/search", duration_ms, 500)
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


# =============================================================================
# Analytics Endpoints
# =============================================================================

@app.get("/v1/analytics", response_model=AnalyticsSummaryResponse, tags=["analytics"])
async def analytics_summary():
    """Get analytics system summary and available endpoints"""
    return AnalyticsSummaryResponse(
        status="available",
        tracked_metrics=["requests", "chats", "memory_searches"],
        endpoints=[
            "/v1/analytics/stats",
        ],
        retention_days=30,
    )


@app.post("/v1/analytics/stats", response_model=AnalyticsStatsResponse, tags=["analytics"])
@app.get("/v1/analytics/stats", response_model=AnalyticsStatsResponse, tags=["analytics"])
async def analytics_stats(days: int = 7):
    """
    Get usage analytics and statistics.
    
    - **days**: Number of days to look back (1-90, default: 7)
    
    Returns aggregated metrics including request counts, response times,
    chat usage, token consumption, and error rates.
    """
    try:
        stats = analytics.get_stats(days=days)
        return AnalyticsStatsResponse(**stats)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analytics error: {str(e)}",
        )


@app.websocket("/v1/chat/stream/{session_id}")
async def chat_stream(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time streaming chat.
    
    Connect to this endpoint for token-by-token streaming responses.
    
    Message format (JSON):
    {
        "message": "Your message here",
        "provider": "openai" | "anthropic" (optional),
        "model": "model-name" (optional),
        "temperature": 0.7 (optional),
        "max_tokens": 1024 (optional),
        "system_prompt": "custom prompt" (optional),
        "use_memory": true (optional, default: true)
    }
    """
    await manager.connect(websocket, session_id)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            
            # Extract parameters
            user_message = data.get("message", "")
            provider = data.get("provider")
            model = data.get("model")
            temperature = data.get("temperature", 0.7)
            max_tokens = data.get("max_tokens")
            system_prompt = data.get("system_prompt")
            use_memory = data.get("use_memory", True)
            
            if not user_message:
                await manager.send_to_client(websocket, {
                    "type": "error",
                    "error": "Message is required",
                })
                continue
            
            # Retrieve memories if enabled
            memories = []
            if use_memory and session_id:
                memories = await memory.search(
                    query=user_message,
                    top_k=5,
                    filter_metadata={"session_id": session_id},
                )
            
            # Build system prompt with memories
            final_system_prompt = system_prompt or (
                "You are MasterClaw, an AI familiar bound to Rex deus. "
                "Be helpful, direct, and slightly mischievous when appropriate."
            )
            
            if memories:
                memory_context = "\n\nRelevant context from memory:\n" + "\n".join(
                    f"- {m.content}" for m in memories
                )
                final_system_prompt += memory_context
            
            # Send start event
            await manager.send_to_client(websocket, {
                "type": "start",
                "session_id": session_id,
                "model": model or "default",
                "provider": provider or "openai",
            })
            
            # Stream the response
            full_response = ""
            try:
                llm_provider = llm_router.get_provider(provider or "openai")
                
                async for token in llm_provider.stream(
                    message=user_message,
                    system_prompt=final_system_prompt,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                ):
                    full_response += token
                    await manager.send_to_client(websocket, {
                        "type": "token",
                        "token": token,
                    })
                
                # Send completion event
                await manager.send_to_client(websocket, {
                    "type": "complete",
                    "response": full_response,
                    "memories_used": len(memories),
                })
                
                # Store interaction in memory
                if session_id:
                    await memory.add(
                        content=f"User: {user_message}\nAssistant: {full_response}",
                        metadata={
                            "session_id": session_id,
                            "type": "chat_interaction",
                            "provider": provider or "openai",
                        },
                        source="chat_stream",
                    )
                    
            except ValueError as e:
                await manager.send_to_client(websocket, {
                    "type": "error",
                    "error": str(e),
                    "code": "INVALID_PROVIDER",
                })
            except Exception as e:
                await manager.send_to_client(websocket, {
                    "type": "error",
                    "error": f"Streaming error: {str(e)}",
                    "code": "STREAM_ERROR",
                })
                
    except WebSocketDisconnect:
        manager.disconnect(websocket, session_id)
    except Exception as e:
        # Handle any unexpected errors
        try:
            await manager.send_to_client(websocket, {
                "type": "error",
                "error": str(e),
                "code": "WEBSOCKET_ERROR",
            })
        except:
            pass
        finally:
            manager.disconnect(websocket, session_id)
