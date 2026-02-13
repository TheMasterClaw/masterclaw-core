"""Main FastAPI application for MasterClaw Core"""

import logging
import sys
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import FastAPI, HTTPException, status, WebSocket, WebSocketDisconnect, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import Response, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

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
    SessionListResponse,
    SessionInfo,
    SessionHistoryResponse,
    SessionDeleteResponse,
    PaginationParams,
    SessionHistoryParams,
)

from .analytics import analytics
from .llm import router as llm_router
from .memory import get_memory_store, MemoryStore
from .websocket import manager
from .middleware import (
    RequestLoggingMiddleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
)
from .exceptions import (
    MasterClawException,
    masterclaw_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    general_exception_handler,
)
from . import metrics as prom_metrics

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("masterclaw")


# Global memory store
memory: MemoryStore = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    global memory
    
    # Startup
    logger.info(f"🐾 MasterClaw Core v{__version__} starting...")
    
    # Log security configuration report
    security_report = settings.get_security_report()
    if security_report["is_production"]:
        if security_report["secure"]:
            logger.info("✅ Security configuration check passed")
        else:
            logger.warning("⚠️  Security configuration issues detected:")
            for issue in security_report["issues"]:
                logger.warning(f"   - {issue}")
    
    if security_report["recommendations"]:
        logger.info("💡 Configuration recommendations:")
        for rec in security_report["recommendations"]:
            logger.info(f"   - {rec}")
    
    memory = get_memory_store()
    logger.info(f"✅ Memory store initialized ({settings.MEMORY_BACKEND})")
    logger.info(f"✅ LLM providers: {llm_router.list_providers()}")
    
    yield
    
    # Shutdown
    logger.info("🛑 MasterClaw Core shutting down...")


# Create FastAPI app
app = FastAPI(
    title="MasterClaw Core",
    description="The AI brain behind MasterClaw",
    version=__version__,
    lifespan=lifespan,
)

# Register exception handlers
app.add_exception_handler(MasterClawException, masterclaw_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# Add security and logging middleware (order matters - last added = first executed)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware, requests_per_minute=settings.RATE_LIMIT_PER_MINUTE)
app.add_middleware(RequestLoggingMiddleware)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
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
            "/health/security",
            "/metrics",
            "/v1/chat",
            "/v1/chat/stream/{session_id} (WebSocket)",
            "/v1/memory/search",
            "/v1/memory/add",
            "/v1/memory/{memory_id}",
            "/v1/analytics",
            "/v1/analytics/stats",
            "/v1/sessions",
            "/v1/sessions/{session_id}",
            "/v1/sessions/{session_id} (DELETE)",
            "/v1/sessions/stats/summary",
        ],
    }


@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check():
    """Health check endpoint"""
    services = {
        "memory": settings.MEMORY_BACKEND,
        "llm_providers": llm_router.list_providers(),
        "prometheus_metrics": True,
    }
    
    return HealthResponse(
        status="healthy",
        version=__version__,
        services=services,
    )


@app.get("/health/security", tags=["health"])
async def security_health_check():
    """
    Security configuration health check.
    
    Returns security status without exposing sensitive values.
    Use this endpoint to monitor configuration security in production.
    """
    report = settings.get_security_report()
    
    # Remove any potentially sensitive info
    safe_report = {
        "status": "secure" if report["secure"] else "insecure",
        "environment": report["environment"],
        "is_production": report["is_production"],
        "issues_count": len(report["issues"]),
        "recommendations_count": len(report["recommendations"]),
        "has_llm_provider": report["has_openai_key"] or report["has_anthropic_key"],
        "cors_origins_configured": report["cors_origins_count"] > 0,
        "rate_limit": report["rate_limit"],
    }
    
    status_code = 200 if report["secure"] else 503
    return JSONResponse(content=safe_report, status_code=status_code)


@app.get("/metrics", tags=["monitoring"])
async def metrics_endpoint():
    """
    Prometheus metrics endpoint.
    
    Returns metrics in Prometheus exposition format for scraping.
    Includes HTTP request metrics, chat usage, memory operations, and more.
    """
    return prom_metrics.get_metrics_response()


@app.post("/v1/chat", response_model=ChatResponse, tags=["chat"])
async def chat(request: ChatRequest, http_request: Request):
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
        
        # Track analytics and Prometheus metrics
        duration_ms = (time.time() - start_time) * 1000
        analytics.track_request("/v1/chat", duration_ms, 200)
        analytics.track_chat(
            provider=result["provider"],
            model=result["model"],
            tokens_used=result.get("tokens_used", 0),
        )
        prom_metrics.track_request("POST", "/v1/chat", 200, duration_ms)
        prom_metrics.track_chat(
            provider=result["provider"],
            model=result["model"],
            tokens=result.get("tokens_used", 0)
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
        prom_metrics.track_request("POST", "/v1/chat", status_code, duration_ms)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        status_code = 500
        duration_ms = (time.time() - start_time) * 1000
        analytics.track_request("/v1/chat", duration_ms, status_code)
        prom_metrics.track_request("POST", "/v1/chat", status_code, duration_ms)
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
        
        # Track analytics and Prometheus metrics
        duration_ms = (time.time() - start_time) * 1000
        analytics.track_request("/v1/memory/search", duration_ms, 200)
        analytics.track_memory_search(len(results), duration_ms)
        prom_metrics.track_request("POST", "/v1/memory/search", 200, duration_ms)
        prom_metrics.track_memory_search(duration_ms)
        prom_metrics.track_memory_operation("search", success=True)
        
        return MemorySearchResponse(
            query=request.query,
            results=results,
            total_results=len(results),
        )
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        analytics.track_request("/v1/memory/search", duration_ms, 500)
        prom_metrics.track_request("POST", "/v1/memory/search", 500, duration_ms)
        prom_metrics.track_memory_operation("search", success=False)
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
        
        prom_metrics.track_memory_operation("add", success=True)
        
        return {
            "success": True,
            "memory_id": memory_id,
            "message": "Memory added successfully",
        }
    except Exception as e:
        prom_metrics.track_memory_operation("add", success=False)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Add error: {str(e)}",
        )


@app.get("/v1/memory/{memory_id}", response_model=MemoryEntry, tags=["memory"])
async def get_memory(memory_id: str):
    """Get a specific memory by ID"""
    result = await memory.get(memory_id)
    if not result:
        prom_metrics.track_memory_operation("get", success=False)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Memory not found",
        )
    prom_metrics.track_memory_operation("get", success=True)
    return result


@app.delete("/v1/memory/{memory_id}", response_model=dict, tags=["memory"])
async def delete_memory(memory_id: str):
    """Delete a memory by ID"""
    success = await memory.delete(memory_id)
    if not success:
        prom_metrics.track_memory_operation("delete", success=False)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Memory not found",
        )
    prom_metrics.track_memory_operation("delete", success=True)
    return {
        "success": True,
        "message": "Memory deleted successfully",
    }


# =============================================================================
# Session Management Endpoints
# =============================================================================

@app.get("/v1/sessions", response_model=SessionListResponse, tags=["sessions"])
async def list_sessions(
    params: PaginationParams = Depends(),
    active_since_hours: Optional[int] = None
):
    """
    List all chat sessions.
    
    - **limit**: Maximum number of sessions to return (1-500, default: 100)
    - **offset**: Pagination offset (default: 0)
    - **active_since_hours**: Only show sessions active within last N hours (optional)
    
    Returns session IDs, creation times, last activity, and message counts.
    """
    try:
        # Search for all chat interaction memories to extract sessions
        all_memories = await memory.search(
            query="chat_interaction",
            top_k=params.limit + params.offset,
            filter_metadata={"type": "chat_interaction"}
        )
        
        # Group memories by session_id
        sessions_dict: Dict[str, Dict[str, Any]] = {}
        
        for mem in all_memories:
            session_id = mem.metadata.get("session_id")
            if not session_id:
                continue
            
            if session_id not in sessions_dict:
                sessions_dict[session_id] = {
                    "session_id": session_id,
                    "created_at": mem.timestamp,
                    "last_active": mem.timestamp,
                    "message_count": 0,
                    "metadata": {"sources": set()}
                }
            
            session = sessions_dict[session_id]
            session["message_count"] += 1
            
            # Track earliest and latest timestamps
            if mem.timestamp < session["created_at"]:
                session["created_at"] = mem.timestamp
            if mem.timestamp > session["last_active"]:
                session["last_active"] = mem.timestamp
            
            # Track sources
            if mem.source:
                session["metadata"]["sources"].add(mem.source)
        
        # Convert sets to lists for JSON serialization
        for session in sessions_dict.values():
            session["metadata"]["sources"] = list(session["metadata"]["sources"])
        
        # Filter by active_since if specified
        if active_since_hours:
            from datetime import timedelta
            cutoff = datetime.utcnow() - timedelta(hours=active_since_hours)
            sessions_dict = {
                sid: s for sid, s in sessions_dict.items()
                if s["last_active"] >= cutoff
            }
        
        # Sort by last_active (newest first)
        sorted_sessions = sorted(
            sessions_dict.values(),
            key=lambda x: x["last_active"],
            reverse=True
        )
        
        # Apply pagination
        total = len(sorted_sessions)
        paginated = sorted_sessions[params.offset:params.offset + params.limit]
        
        # Convert to SessionInfo objects
        sessions = [
            SessionInfo(
                session_id=s["session_id"],
                created_at=s["created_at"],
                last_active=s["last_active"],
                message_count=s["message_count"],
                metadata=s["metadata"]
            )
            for s in paginated
        ]
        
        prom_metrics.track_request("GET", "/v1/sessions", 200, 0)
        
        return SessionListResponse(
            sessions=sessions,
            total=total,
            limit=params.limit,
            offset=params.offset
        )
    
    except Exception as e:
        prom_metrics.track_request("GET", "/v1/sessions", 500, 0)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Session list error: {str(e)}"
        )


@app.get("/v1/sessions/{session_id}", response_model=SessionHistoryResponse, tags=["sessions"])
async def get_session_history(
    session_id: str,
    params: SessionHistoryParams = Depends()
):
    """
    Get detailed chat history for a specific session.
    
    - **session_id**: The session identifier
    - **limit**: Maximum messages to return (1-100, default: 50)
    - **offset**: Pagination offset (default: 0)
    
    Returns all messages in the session with timestamps.
    """
    try:
        # Search for memories with this session_id
        all_memories = await memory.search(
            query="",
            top_k=1000,  # Get all to filter and sort
            filter_metadata={
                "session_id": session_id,
                "type": "chat_interaction"
            }
        )
        
        if not all_memories:
            prom_metrics.track_request("GET", "/v1/sessions/{id}", 404, 0)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session '{session_id}' not found or has no messages"
            )
        
        # Sort by timestamp (oldest first for conversation flow)
        all_memories.sort(key=lambda m: m.timestamp)
        
        # Calculate session duration
        first_msg = all_memories[0].timestamp
        last_msg = all_memories[-1].timestamp
        duration_minutes = (last_msg - first_msg).total_seconds() / 60
        
        # Apply pagination
        total = len(all_memories)
        paginated = all_memories[params.offset:params.offset + params.limit]
        
        prom_metrics.track_request("GET", "/v1/sessions/{id}", 200, 0)
        
        return SessionHistoryResponse(
            session_id=session_id,
            messages=paginated,
            total_messages=total,
            session_duration_minutes=duration_minutes if total > 1 else None
        )
    
    except HTTPException:
        raise
    except Exception as e:
        prom_metrics.track_request("GET", "/v1/sessions/{id}", 500, 0)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Session history error: {str(e)}"
        )


@app.delete("/v1/sessions/{session_id}", response_model=SessionDeleteResponse, tags=["sessions"])
async def delete_session(session_id: str):
    """
    Delete a session and all associated chat memories.
    
    - **session_id**: The session identifier to delete
    
    Returns the number of memories deleted.
    """
    try:
        # Find all memories for this session
        all_memories = await memory.search(
            query="",
            top_k=1000,
            filter_metadata={"session_id": session_id}
        )
        
        deleted_count = 0
        for mem in all_memories:
            if mem.id and await memory.delete(mem.id):
                deleted_count += 1
        
        prom_metrics.track_memory_operation("delete", success=True)
        
        return SessionDeleteResponse(
            success=True,
            session_id=session_id,
            memories_deleted=deleted_count,
            message=f"Session '{session_id}' deleted with {deleted_count} associated memories"
        )
    
    except Exception as e:
        prom_metrics.track_memory_operation("delete", success=False)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Session deletion error: {str(e)}"
        )


@app.get("/v1/sessions/stats/summary", tags=["sessions"])
async def get_session_stats():
    """
    Get aggregate session statistics.
    
    Returns overall session metrics including total sessions, 
    average messages per session, and active sessions in last 24h.
    """
    try:
        # Get all sessions first
        sessions_response = await list_sessions(limit=500, offset=0)
        sessions = sessions_response.sessions
        
        from datetime import timedelta
        
        # Calculate stats
        total_sessions = len(sessions)
        total_messages = sum(s.message_count for s in sessions)
        avg_messages = total_messages / total_sessions if total_sessions > 0 else 0
        
        # Active in last 24 hours
        cutoff_24h = datetime.utcnow() - timedelta(hours=24)
        active_24h = sum(1 for s in sessions if s.last_active >= cutoff_24h)
        
        # Active in last 7 days
        cutoff_7d = datetime.utcnow() - timedelta(days=7)
        active_7d = sum(1 for s in sessions if s.last_active >= cutoff_7d)
        
        prom_metrics.track_request("GET", "/v1/sessions/stats/summary", 200, 0)
        
        return {
            "total_sessions": total_sessions,
            "total_messages": total_messages,
            "average_messages_per_session": round(avg_messages, 2),
            "active_sessions_24h": active_24h,
            "active_sessions_7d": active_7d,
            "timestamp": datetime.utcnow()
        }
    
    except Exception as e:
        prom_metrics.track_request("GET", "/v1/sessions/stats/summary", 500, 0)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Session stats error: {str(e)}"
        )

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
    
    Security features:
    - Session ID validation (alphanumeric, 1-64 chars)
    - Max 5 concurrent connections per session
    - Max 10 concurrent connections per IP
    - Rate limiting: 100 messages per 60 seconds
    - Max message size: 64KB
    - Connection timeout: 1 hour
    
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
    connected = await manager.connect(websocket, session_id)
    if not connected:
        return  # Connection was rejected by security checks
    
    try:
        while True:
            # Receive and validate message using security-hardened method
            data = await manager.validate_and_receive(websocket)
            
            if data is None:
                continue  # Validation failed, error already sent
            
            # Extract parameters with validation
            user_message = data.get("message", "")
            if not isinstance(user_message, str):
                await manager.send_to_client(websocket, {
                    "type": "error",
                    "error": "Message must be a string",
                    "code": "INVALID_MESSAGE_TYPE",
                })
                continue
            
            provider = data.get("provider")
            model = data.get("model")
            temperature = data.get("temperature", 0.7)
            max_tokens = data.get("max_tokens")
            system_prompt = data.get("system_prompt")
            use_memory = data.get("use_memory", True)
            
            if not user_message.strip():
                await manager.send_to_client(websocket, {
                    "type": "error",
                    "error": "Message is required and cannot be empty",
                    "code": "EMPTY_MESSAGE",
                })
                continue
            
            # Validate temperature range
            if not isinstance(temperature, (int, float)) or not (0 <= temperature <= 2):
                await manager.send_to_client(websocket, {
                    "type": "error",
                    "error": "Temperature must be between 0 and 2",
                    "code": "INVALID_TEMPERATURE",
                })
                continue
            
            # Validate max_tokens
            if max_tokens is not None:
                if not isinstance(max_tokens, int) or max_tokens < 1 or max_tokens > 32000:
                    await manager.send_to_client(websocket, {
                        "type": "error",
                        "error": "max_tokens must be between 1 and 32000",
                        "code": "INVALID_MAX_TOKENS",
                    })
                    continue
            
            # Retrieve memories if enabled
            memories = []
            if use_memory and session_id:
                try:
                    memories = await memory.search(
                        query=user_message,
                        top_k=5,
                        filter_metadata={"session_id": session_id},
                    )
                except Exception as e:
                    logger.error(f"Memory search error in websocket: {e}")
                    # Continue without memories rather than failing
            
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
                    try:
                        await memory.add(
                            content=f"User: {user_message}\nAssistant: {full_response}",
                            metadata={
                                "session_id": session_id,
                                "type": "chat_interaction",
                                "provider": provider or "openai",
                            },
                            source="chat_stream",
                        )
                    except Exception as e:
                        logger.error(f"Failed to store memory: {e}")
                        # Don't fail the response if memory storage fails
                        
            except ValueError as e:
                await manager.send_to_client(websocket, {
                    "type": "error",
                    "error": str(e),
                    "code": "INVALID_PROVIDER",
                })
            except Exception as e:
                logger.error(f"Streaming error: {e}")
                await manager.send_to_client(websocket, {
                    "type": "error",
                    "error": f"Streaming error: {str(e)}",
                    "code": "STREAM_ERROR",
                })
                
    except WebSocketDisconnect:
        manager.disconnect(websocket, session_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await manager.send_to_client(websocket, {
                "type": "error",
                "error": "Internal server error",
                "code": "INTERNAL_ERROR",
            })
        except:
            pass
        finally:
            manager.disconnect(websocket, session_id)
