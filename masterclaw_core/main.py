"""Main FastAPI application for MasterClaw Core"""

import logging
import sys
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
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
    BatchMemoryImportRequest,
    BatchMemoryImportResponse,
    MemoryExportRequest,
    MemoryExportResponse,
    HealthResponse,
    AnalyticsStatsRequest,
    AnalyticsStatsResponse,
    AnalyticsSummaryResponse,
    SessionListResponse,
    SessionInfo,
    SessionHistoryResponse,
    SessionDeleteResponse,
    BulkSessionDeleteRequest,
    BulkSessionDeleteResponse,
    PaginationParams,
    SessionHistoryParams,
    CostSummaryRequest,
    CostSummaryResponse,
    DailyCostsResponse,
    PricingResponse,
    PricingInfo,
    ProviderCostBreakdown,
    ModelCostBreakdown,
    SessionCostBreakdown,
    DailyCostEntry,
    SystemInfoResponse,
    ComponentHealth,
    FeatureAvailability,
)

from .analytics import analytics
from .llm import router as llm_router
from .memory import get_memory_store, MemoryStore
from .websocket import manager
from .tools import registry as tool_registry
from .middleware import (
    RequestLoggingMiddleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    IPBlockMiddleware,
)
from .exceptions import (
    MasterClawException,
    masterclaw_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    general_exception_handler,
    get_secure_error_message,
    raise_secure_http_exception,
    secure_endpoint,
)
from . import metrics as prom_metrics
from .security import validate_session_id
from .security_response import (
    auto_responder,
    initialize_auto_responder,
    shutdown_auto_responder,
)
from .tasks import task_queue

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

# Server start time for uptime calculation
SERVER_START_TIME: datetime = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    global memory, SERVER_START_TIME

    # Startup
    SERVER_START_TIME = datetime.utcnow()
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

    # Log config issues (in any environment)
    if security_report.get("config_issues"):
        logger.warning("⚠️  Configuration issues detected:")
        for issue in security_report["config_issues"]:
            logger.warning(f"   - {issue}")

    if security_report["recommendations"]:
        logger.info("💡 Configuration recommendations:")
        for rec in security_report["recommendations"]:
            logger.info(f"   - {rec}")

    memory = get_memory_store()
    logger.info(f"✅ Memory store initialized ({settings.MEMORY_BACKEND})")
    logger.info(f"✅ LLM providers: {llm_router.list_providers()}")

    # Initialize security auto-responder
    await initialize_auto_responder()
    logger.info("✅ Security auto-responder initialized")

    # Start background task queue
    await task_queue.start()
    logger.info(f"✅ Task queue started ({task_queue.max_workers} workers)")

    yield

    # Shutdown
    logger.info("🛑 MasterClaw Core shutting down...")

    # Shutdown task queue gracefully
    await task_queue.stop()
    logger.info("✅ Task queue shutdown complete")

    # Shutdown security auto-responder
    await shutdown_auto_responder()
    logger.info("✅ Security auto-responder shutdown complete")


# Create FastAPI app with interactive API documentation
app = FastAPI(
    title="MasterClaw Core",
    description="""
    The AI brain behind MasterClaw - LLM integrations, memory systems, and agent orchestration.

    ## Features

    - **Chat**: Send messages to AI with memory context
    - **Memory**: Semantic search and storage with ChromaDB
    - **Sessions**: Manage conversation sessions
    - **Analytics**: Cost tracking and usage statistics
    - **Streaming**: Real-time WebSocket chat

    ## Authentication

    API endpoints require a valid API key passed in the `X-API-Key` header.
    """,
    version=__version__,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    openapi_tags=[
        {"name": "root", "description": "Root and health endpoints"},
        {"name": "health", "description": "Health, security, and system information"},
        {"name": "security", "description": "Security management - IP blocking and auto-response"},
        {"name": "monitoring", "description": "Prometheus metrics and monitoring"},
        {"name": "chat", "description": "AI chat and conversation"},
        {"name": "memory", "description": "Memory storage and semantic search"},
        {"name": "sessions", "description": "Session management"},
        {"name": "analytics", "description": "Usage analytics and statistics"},
        {"name": "costs", "description": "LLM cost tracking and pricing"},
        {"name": "tools", "description": "Tool use framework - GitHub, system, weather"},
    ],
)

# Register exception handlers
app.add_exception_handler(MasterClawException, masterclaw_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# Add security and logging middleware (order matters - last added = first executed)
# IP Block middleware should be first to block banned IPs immediately
app.add_middleware(IPBlockMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    RateLimitMiddleware,
    requests_per_minute=settings.RATE_LIMIT_PER_MINUTE,
    window_seconds=60,
    max_ips_tracked=10000,
    cleanup_interval=1000
)
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
    """Root endpoint with API documentation links"""
    return {
        "name": "MasterClaw Core",
        "version": __version__,
        "status": "running",
        "documentation": {
            "swagger_ui": "/docs",
            "redoc": "/redoc",
            "openapi_schema": "/openapi.json",
        },
        "endpoints": [
            "/health",
            "/health/security",
            "/info",
            "/metrics",
            "/v1/chat",
            "/v1/chat/stream/{session_id} (WebSocket)",
            "/v1/memory/search",
            "/v1/memory/add",
            "/v1/memory/{memory_id}",
            "/v1/memory/batch",
            "/v1/memory/export",
            "/v1/analytics",
            "/v1/analytics/stats",
            "/v1/costs",
            "/v1/costs/daily",
            "/v1/costs/pricing",
            "/v1/sessions",
            "/v1/sessions/{session_id}",
            "/v1/sessions/{session_id} (DELETE)",
            "/v1/sessions/bulk-delete (NEW)",
            "/v1/sessions/stats/summary",
            "/v1/tools",
            "/v1/tools/{tool_name}",
            "/v1/tools/execute",
            "/v1/tools/definitions/openai",
        ],
    }


@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check():
    """Health check endpoint"""
    services = {
        "memory": settings.MEMORY_BACKEND,
        "llm_providers": llm_router.list_providers(),
        "prometheus_metrics": True,
        "task_queue": {
            "running": task_queue.running,
            "workers": task_queue.max_workers,
            "queue_size": task_queue.get_queue_size(),
        },
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
        "config_issues_count": len(report.get("config_issues", [])),
        "recommendations_count": len(report["recommendations"]),
        "has_llm_provider": report["has_openai_key"] or report["has_anthropic_key"],
        "cors_origins_configured": report["cors_origins_count"] > 0,
        "rate_limit": report["rate_limit"],
    }

    status_code = 200 if report["secure"] else 503
    return JSONResponse(content=safe_report, status_code=status_code)


@app.get("/info", response_model=SystemInfoResponse, tags=["health"])
async def system_info(http_request: Request):
    """
    Get comprehensive system information and component health.

    Returns detailed information about:
    - API version and environment
    - Component health (memory store, LLM providers, task queue)
    - Available features and their status
    - System configuration (rate limits, CORS, etc.)
    - Active session count

    Use this endpoint for:
    - Dashboard health displays
    - CLI version/info commands
    - Monitoring and alerting
    - Debugging and troubleshooting
    """
    import time
    start_time = time.time()

    # Calculate uptime
    uptime_seconds = None
    if SERVER_START_TIME:
        uptime_seconds = int((datetime.utcnow() - SERVER_START_TIME).total_seconds())

    # Check component health
    components = []
    overall_health = "healthy"

    # Check memory store
    try:
        mem_start = time.time()
        await memory.search("health_check", top_k=1)
        mem_response_ms = (time.time() - mem_start) * 1000
        components.append(ComponentHealth(
            name="memory_store",
            status="healthy",
            version=settings.MEMORY_BACKEND,
            details=f"{settings.MEMORY_BACKEND} backend responding",
            response_time_ms=round(mem_response_ms, 2)
        ))
    except Exception as e:
        overall_health = "degraded"
        components.append(ComponentHealth(
            name="memory_store",
            status="unhealthy",
            details=str(e)
        ))

    # Check LLM providers
    try:
        providers = llm_router.list_providers()
        for provider in providers:
            try:
                # Quick health check by listing available models
                prov_start = time.time()
                llm_router.get_provider(provider)
                prov_response_ms = (time.time() - prov_start) * 1000
                components.append(ComponentHealth(
                    name=f"llm_{provider}",
                    status="healthy",
                    details=f"Provider available",
                    response_time_ms=round(prov_response_ms, 2)
                ))
            except Exception as e:
                overall_health = "degraded"
                components.append(ComponentHealth(
                    name=f"llm_{provider}",
                    status="unhealthy",
                    details=str(e)
                ))
    except Exception as e:
        overall_health = "degraded"
        components.append(ComponentHealth(
            name="llm_router",
            status="unhealthy",
            details=str(e)
        ))

    # Check task queue
    try:
        components.append(ComponentHealth(
            name="task_queue",
            status="healthy" if task_queue.running else "degraded",
            details=f"{task_queue.max_workers} workers, {task_queue.get_queue_size()} queued",
        ))
    except Exception as e:
        overall_health = "degraded"
        components.append(ComponentHealth(
            name="task_queue",
            status="unhealthy",
            details=str(e)
        ))

    # Build features list
    features = [
        FeatureAvailability(
            name="chat",
            available=True,
            description="AI chat with memory context"
        ),
        FeatureAvailability(
            name="memory",
            available=settings.MEMORY_BACKEND != "none",
            description="Vector memory storage and semantic search"
        ),
        FeatureAvailability(
            name="streaming",
            available=True,
            description="WebSocket streaming chat"
        ),
        FeatureAvailability(
            name="analytics",
            available=True,
            description="Usage analytics and cost tracking"
        ),
        FeatureAvailability(
            name="tools",
            available=True,
            description="Tool use framework"
        ),
        FeatureAvailability(
            name="sessions",
            available=True,
            description="Session management"
        ),
        FeatureAvailability(
            name="batch_operations",
            available=True,
            description="Bulk memory import/export"
        ),
    ]

    # Get active session count (approximate from recent memories)
    try:
        recent_cutoff = datetime.utcnow() - timedelta(hours=24)
        all_sessions = await memory.search(
            query="chat_interaction",
            top_k=1000,
            filter_metadata={"type": "chat_interaction"}
        )
        # Count unique sessions from last 24h
        active_sessions = len(set(
            m.metadata.get("session_id")
            for m in all_sessions
            if m.metadata.get("session_id") and m.timestamp >= recent_cutoff
        ))
    except Exception:
        active_sessions = 0

    # Build response
    response = SystemInfoResponse(
        version=__version__,
        environment=settings.ENVIRONMENT,
        timestamp=datetime.utcnow(),
        uptime_seconds=uptime_seconds,
        components=components,
        overall_health=overall_health,
        features=features,
        memory_backend=settings.MEMORY_BACKEND,
        llm_providers=llm_router.list_providers(),
        active_sessions=active_sessions,
        api_documentation={
            "swagger_ui": "/docs",
            "redoc": "/redoc",
            "openapi": "/openapi.json",
        },
        rate_limit={
            "requests_per_minute": settings.RATE_LIMIT_PER_MINUTE,
            "window_seconds": 60,
        }
    )

    # Track metrics
    duration_ms = (time.time() - start_time) * 1000
    prom_metrics.track_request("GET", "/info", 200, duration_ms)

    return response


@app.get("/security/blocks", tags=["security"])
async def list_blocked_ips():
    """
    List all currently blocked IP addresses.

    Returns a list of blocked IPs with their block reasons and expiration times.
    Requires admin API key.
    """
    blocked = auto_responder.list_blocked_ips()

    return {
        "blocked_ips": [
            {
                "ip_address": b.ip_address,
                "blocked_at": b.blocked_at.isoformat(),
                "expires_at": b.expires_at.isoformat(),
                "reason": b.reason.value,
                "threat_level": b.threat_level,
                "blocked_by": b.blocked_by,
            }
            for b in blocked
        ],
        "total": len(blocked),
    }


@app.post("/security/blocks", tags=["security"])
async def block_ip_endpoint(
    ip_address: str,
    reason: str = "manual",
    duration_minutes: int = 60,
    threat_level: str = "medium"
):
    """
    Manually block an IP address.

    Args:
        ip_address: The IP address to block
        reason: Block reason (brute_force, rate_limit_violation, suspicious_activity, etc.)
        duration_minutes: How long to block (0 = permanent)
        threat_level: Severity level (low, medium, high, critical)

    Returns the created block record.
    """
    from .security_response import BlockReason

    try:
        blocked = await auto_responder.block_ip(
            ip_address=ip_address,
            reason=BlockReason(reason),
            duration_minutes=duration_minutes,
            threat_level=threat_level,
            blocked_by="manual",
        )

        return {
            "status": "blocked",
            "ip_address": blocked.ip_address,
            "expires_at": blocked.expires_at.isoformat(),
            "reason": blocked.reason.value,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/security/blocks/{ip_address}", tags=["security"])
async def unblock_ip_endpoint(ip_address: str):
    """
    Unblock a previously blocked IP address.

    Returns 404 if the IP was not blocked.
    """
    success = await auto_responder.unblock_ip(ip_address, unblocked_by="manual")

    if not success:
        raise HTTPException(status_code=404, detail=f"IP {ip_address} is not blocked")

    return {
        "status": "unblocked",
        "ip_address": ip_address,
    }


@app.get("/security/auto-responder/stats", tags=["security"])
async def auto_responder_stats():
    """
    Get security auto-responder statistics.

    Returns information about active rules, blocked IPs, and response actions.
    """
    return auto_responder.get_stats()


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

        # Estimate input/output tokens (rough approximation: 1 token ≈ 4 chars)
        input_tokens = result.get("tokens_used", 0) // 2 if result.get("tokens_used") else len(request.message) // 4
        output_tokens = result.get("tokens_used", 0) - input_tokens if result.get("tokens_used") else len(result["response"]) // 4

        analytics.track_chat(
            provider=result["provider"],
            model=result["model"],
            tokens_used=result.get("tokens_used", 0),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            session_id=request.session_id
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

        # Use secure error handling to prevent information leakage
        request_id = getattr(http_request.state, 'request_id', None)
        raise_secure_http_exception(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error=e,
            public_message="Chat processing failed",
            log_message=f"Chat error for session: {request.session_id}",
            request_id=request_id
        )


@app.post("/v1/memory/search", response_model=MemorySearchResponse, tags=["memory"])
async def search_memory(request: MemorySearchRequest, http_request: Request):
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

        # Use secure error handling to prevent information leakage
        request_id = getattr(http_request.state, 'request_id', None)
        raise_secure_http_exception(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error=e,
            public_message="Failed to search memories",
            log_message=f"Memory search failed for query: {request.query[:100]}",
            request_id=request_id
        )


@app.post("/v1/memory/add", response_model=dict, tags=["memory"])
async def add_memory(entry: MemoryEntry, http_request: Request):
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
        request_id = getattr(http_request.state, 'request_id', None)
        raise_secure_http_exception(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error=e,
            public_message="Failed to add memory",
            log_message="Memory add operation failed",
            request_id=request_id
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


@app.post("/v1/memory/batch", response_model=BatchMemoryImportResponse, tags=["memory"])
async def batch_import_memories(
    request: BatchMemoryImportRequest,
    http_request: Request
):
    """
    Batch import multiple memories efficiently.

    - Import up to 1000 memories in a single request
    - Optionally skip duplicates based on content hash
    - Add source prefix to track import origin

    **Use Cases:**
    - Migrating from other systems
    - Restoring from backups
    - Bulk data ingestion

    **Rate Limiting:** This endpoint has stricter rate limits due to resource usage.
    """
    import time
    start_time = time.time()

    imported_ids = []
    errors = []
    skipped = 0

    # Track existing content hashes to detect duplicates within the batch
    seen_content = set()

    for idx, entry in enumerate(request.memories):
        try:
            # Check for duplicates within batch
            content_hash = hash(f"{entry.content}:{entry.source}")
            if request.skip_duplicates and content_hash in seen_content:
                skipped += 1
                continue
            seen_content.add(content_hash)

            # Add source prefix if specified
            source = entry.source
            if request.source_prefix:
                source = f"{request.source_prefix}:{source or 'import'}"

            # Import the memory
            memory_id = await memory.add(
                content=entry.content,
                metadata=entry.metadata,
                source=source,
            )
            imported_ids.append(memory_id)
            prom_metrics.track_memory_operation("add", success=True)

        except Exception as e:
            prom_metrics.track_memory_operation("add", success=False)
            errors.append({
                "index": idx,
                "content_preview": entry.content[:100] if entry.content else "",
                "error": str(e),
            })

    duration_ms = (time.time() - start_time) * 1000

    return BatchMemoryImportResponse(
        success=len(errors) == 0,
        imported_count=len(imported_ids),
        skipped_count=skipped,
        failed_count=len(errors),
        memory_ids=imported_ids,
        errors=errors[:10],  # Limit errors returned
        duration_ms=duration_ms,
    )


@app.post("/v1/memory/export", response_model=MemoryExportResponse, tags=["memory"])
async def export_memories(
    request: MemoryExportRequest,
    http_request: Request
):
    """
    Export memories with optional filtering.

    - Export by search query (semantic similarity)
    - Filter by metadata, source, or date range
    - Up to 5000 memories per request

    **Use Cases:**
    - Creating backups
    - Data migration
    - Analysis and auditing

    **Note:** For large exports, consider using pagination with multiple requests.
    """
    try:
        # Determine search strategy based on request
        if request.query:
            # Semantic search
            results = await memory.search(
                query=request.query,
                top_k=request.limit,
                filter_metadata=request.filter_metadata
            )
        else:
            # Get all memories (empty search returns recent memories)
            results = await memory.search(
                query="*",
                top_k=request.limit,
                filter_metadata=request.filter_metadata
            )

        # Apply additional filters
        filtered_results = []
        for mem in results:
            # Filter by source if specified
            if request.source_filter and mem.source != request.source_filter:
                continue

            # Filter by date if specified
            if request.since and mem.timestamp < request.since:
                continue

            filtered_results.append(mem)

            if len(filtered_results) >= request.limit:
                break

        return MemoryExportResponse(
            success=True,
            memories=filtered_results,
            total_count=len(filtered_results),
            query_applied=request.query,
        )

    except Exception as e:
        request_id = getattr(http_request.state, 'request_id', None)
        raise_secure_http_exception(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error=e,
            public_message="Failed to export memories",
            log_message="Memory export failed",
            request_id=request_id
        )


# =============================================================================
# Session Management Endpoints
# =============================================================================

@app.get("/v1/sessions", response_model=SessionListResponse, tags=["sessions"])
async def list_sessions(
    http_request: Request,
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
        request_id = getattr(http_request.state, 'request_id', None)
        raise_secure_http_exception(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error=e,
            public_message="Failed to list sessions",
            log_message="Session list operation failed",
            request_id=request_id
        )


@app.get("/v1/sessions/{session_id}", response_model=SessionHistoryResponse, tags=["sessions"])
async def get_session_history(
    session_id: str,
    http_request: Request,
    params: SessionHistoryParams = Depends()
):
    """
    Get detailed chat history for a specific session.

    - **session_id**: The session identifier
    - **limit**: Maximum messages to return (1-100, default: 50)
    - **offset**: Pagination offset (default: 0)

    Returns all messages in the session with timestamps.
    """
    # Validate session ID format (security hardening)
    try:
        validated_session_id = validate_session_id(session_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    try:
        # Search for memories with this session_id
        all_memories = await memory.search(
            query="",
            top_k=1000,  # Get all to filter and sort
            filter_metadata={
                "session_id": validated_session_id,
                "type": "chat_interaction"
            }
        )

        if not all_memories:
            prom_metrics.track_request("GET", "/v1/sessions/{id}", 404, 0)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session '{validated_session_id}' not found or has no messages"
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
            session_id=validated_session_id,
            messages=paginated,
            total_messages=total,
            session_duration_minutes=duration_minutes if total > 1 else None
        )

    except HTTPException:
        raise
    except Exception as e:
        prom_metrics.track_request("GET", "/v1/sessions/{id}", 500, 0)
        request_id = getattr(http_request.state, 'request_id', None)
        raise_secure_http_exception(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error=e,
            public_message="Failed to retrieve session history",
            log_message=f"Session history failed for: {validated_session_id}",
            request_id=request_id
        )


@app.delete("/v1/sessions/{session_id}", response_model=SessionDeleteResponse, tags=["sessions"])
async def delete_session(session_id: str, http_request: Request):
    """
    Delete a session and all associated chat memories.

    - **session_id**: The session identifier to delete

    Returns the number of memories deleted.
    """
    # Validate session ID format (security hardening)
    try:
        validated_session_id = validate_session_id(session_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    try:
        # Find all memories for this session
        all_memories = await memory.search(
            query="",
            top_k=1000,
            filter_metadata={"session_id": validated_session_id}
        )

        deleted_count = 0
        for mem in all_memories:
            if mem.id and await memory.delete(mem.id):
                deleted_count += 1

        prom_metrics.track_memory_operation("delete", success=True)

        return SessionDeleteResponse(
            success=True,
            session_id=validated_session_id,
            memories_deleted=deleted_count,
            message=f"Session '{validated_session_id}' deleted with {deleted_count} associated memories"
        )

    except Exception as e:
        prom_metrics.track_memory_operation("delete", success=False)
        request_id = getattr(http_request.state, 'request_id', None)
        raise_secure_http_exception(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error=e,
            public_message="Failed to delete session",
            log_message=f"Session deletion failed for: {validated_session_id}",
            request_id=request_id
        )


@app.get("/v1/sessions/stats/summary", tags=["sessions"])
async def get_session_stats(http_request: Request):
    """
    Get aggregate session statistics.

    Returns overall session metrics including total sessions,
    average messages per session, and active sessions in last 24h.
    """
    try:
        # Get all sessions first
        sessions_response = await list_sessions(http_request=http_request, limit=500, offset=0)
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
        request_id = getattr(http_request.state, 'request_id', None)
        raise_secure_http_exception(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error=e,
            public_message="Failed to retrieve session statistics",
            log_message="Session stats computation failed",
            request_id=request_id
        )


@app.post("/v1/sessions/bulk-delete", response_model=BulkSessionDeleteResponse, tags=["sessions"])
async def bulk_delete_sessions(
    request: BulkSessionDeleteRequest,
    http_request: Request
):
    """
    Bulk delete multiple sessions efficiently.

    Delete sessions by:
    - **session_ids**: Explicit list of session IDs to delete
    - **older_than_days**: Delete all sessions older than N days

    Features:
    - **Dry run mode**: Preview what would be deleted without making changes
    - **Atomic tracking**: Reports exactly what was deleted and what failed
    - **Performance**: Single API call instead of N individual deletes

    **Rate Limiting:** This endpoint has stricter rate limits due to resource usage.
    """
    import time
    start_time = time.time()

    deleted_sessions = []
    failed_sessions = []
    total_memories_deleted = 0

    try:
        # Determine which sessions to delete
        sessions_to_delete = []

        if request.session_ids:
            # Use explicit list
            sessions_to_delete = request.session_ids
        else:
            # Find sessions older than specified days
            cutoff = datetime.utcnow() - timedelta(days=request.older_than_days)

            # Get all sessions (up to 500 for bulk operations)
            sessions_response = await list_sessions(
                http_request=http_request,
                limit=500,
                offset=0
            )

            for session in sessions_response.sessions:
                if session.last_active < cutoff:
                    sessions_to_delete.append(session.session_id)

        # Dry run: return preview without deleting
        if request.dry_run:
            duration_ms = (time.time() - start_time) * 1000
            return BulkSessionDeleteResponse(
                success=True,
                sessions_deleted=0,
                sessions_failed=0,
                memories_deleted=0,
                dry_run=True,
                deleted_session_ids=[],
                failed_session_ids=[],
                duration_ms=duration_ms,
                message=f"DRY RUN: Would delete {len(sessions_to_delete)} sessions"
            )

        # Perform deletions
        for session_id in sessions_to_delete:
            try:
                # Validate session ID
                validated_id = validate_session_id(session_id)

                # Find all memories for this session
                session_memories = await memory.search(
                    query="",
                    top_k=1000,
                    filter_metadata={"session_id": validated_id}
                )

                # Delete all associated memories
                memories_deleted = 0
                for mem in session_memories:
                    if mem.id and await memory.delete(mem.id):
                        memories_deleted += 1

                total_memories_deleted += memories_deleted
                deleted_sessions.append(validated_id)
                prom_metrics.track_memory_operation("delete", success=True)

            except Exception as e:
                failed_sessions.append({
                    "session_id": session_id,
                    "error": str(e)
                })
                prom_metrics.track_memory_operation("delete", success=False)

        duration_ms = (time.time() - start_time) * 1000

        # Track metrics
        prom_metrics.track_request(
            "POST", "/v1/sessions/bulk-delete",
            200 if len(failed_sessions) == 0 else 207,
            duration_ms
        )

        success = len(failed_sessions) == 0

        return BulkSessionDeleteResponse(
            success=success,
            sessions_deleted=len(deleted_sessions),
            sessions_failed=len(failed_sessions),
            memories_deleted=total_memories_deleted,
            dry_run=False,
            deleted_session_ids=deleted_sessions,
            failed_session_ids=failed_sessions,
            duration_ms=duration_ms,
            message=f"Deleted {len(deleted_sessions)} sessions ({total_memories_deleted} memories)" +
                   (f", {len(failed_sessions)} failed" if failed_sessions else "")
        )

    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        prom_metrics.track_request("POST", "/v1/sessions/bulk-delete", 500, duration_ms)

        request_id = getattr(http_request.state, 'request_id', None)
        raise_secure_http_exception(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error=e,
            public_message="Failed to perform bulk session deletion",
            log_message=f"Bulk delete failed: {str(e)[:200]}",
            request_id=request_id
        )


@app.get("/v1/analytics", response_model=AnalyticsSummaryResponse, tags=["analytics"])
async def analytics_summary():
    """Get analytics system summary and available endpoints"""
    return AnalyticsSummaryResponse(
        status="available",
        tracked_metrics=["requests", "chats", "memory_searches", "costs"],
        endpoints=[
            "/v1/analytics/stats",
            "/v1/costs",
            "/v1/costs/daily",
            "/v1/costs/pricing",
        ],
        retention_days=30,
    )


@app.post("/v1/analytics/stats", response_model=AnalyticsStatsResponse, tags=["analytics"])
@app.get("/v1/analytics/stats", response_model=AnalyticsStatsResponse, tags=["analytics"])
async def analytics_stats(http_request: Request, days: int = 7):
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
        request_id = getattr(http_request.state, 'request_id', None)
        raise_secure_http_exception(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error=e,
            public_message="Failed to retrieve analytics",
            log_message=f"Analytics stats failed for days={days}",
            request_id=request_id
        )


# =============================================================================
# Cost Tracking Endpoints
# =============================================================================

@app.get("/v1/costs", response_model=CostSummaryResponse, tags=["costs"])
async def get_costs(http_request: Request, days: int = 30):
    """
    Get LLM usage cost summary.

    - **days**: Number of days to look back (1-365, default: 30)

    Returns cost breakdown by provider, model, and top sessions.
    Costs are in USD.
    """
    try:
        summary = analytics.cost_tracker.get_cost_summary(days=days)

        # Convert dicts to proper model instances
        by_provider = {
            k: ProviderCostBreakdown(**v) for k, v in summary["by_provider"].items()
        }
        by_model = {
            k: ModelCostBreakdown(**v) for k, v in summary["by_model"].items()
        }
        top_sessions = [
            SessionCostBreakdown(**s) for s in summary["top_sessions"]
        ]

        return CostSummaryResponse(
            period_days=summary["period_days"],
            total_cost=summary["total_cost"],
            total_input_cost=summary["total_input_cost"],
            total_output_cost=summary["total_output_cost"],
            total_tokens=summary["total_tokens"],
            total_input_tokens=summary["total_input_tokens"],
            total_output_tokens=summary["total_output_tokens"],
            total_requests=summary["total_requests"],
            average_cost_per_request=summary["average_cost_per_request"],
            by_provider=by_provider,
            by_model=by_model,
            top_sessions=top_sessions,
            timestamp=datetime.utcnow(),
        )
    except Exception as e:
        request_id = getattr(http_request.state, 'request_id', None)
        raise_secure_http_exception(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error=e,
            public_message="Failed to retrieve cost summary",
            log_message=f"Cost summary failed for days={days}",
            request_id=request_id
        )


@app.get("/v1/costs/daily", response_model=DailyCostsResponse, tags=["costs"])
async def get_daily_costs(http_request: Request, days: int = 30):
    """
    Get daily cost breakdown.

    - **days**: Number of days to look back (1-365, default: 30)

    Returns cost per day for trend analysis.
    """
    try:
        daily = analytics.cost_tracker.get_daily_costs(days=days)
        return DailyCostsResponse(
            days=days,
            daily_costs=[DailyCostEntry(**d) for d in daily],
            timestamp=datetime.utcnow(),
        )
    except Exception as e:
        request_id = getattr(http_request.state, 'request_id', None)
        raise_secure_http_exception(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error=e,
            public_message="Failed to retrieve daily costs",
            log_message=f"Daily costs failed for days={days}",
            request_id=request_id
        )


@app.get("/v1/costs/pricing", response_model=PricingResponse, tags=["costs"])
async def get_pricing(http_request: Request):
    """
    Get current pricing information for all supported models.

    Returns pricing per 1K tokens for input and output.
    """
    from .analytics import PRICING

    try:
        providers = {}
        for provider, models in PRICING.items():
            providers[provider] = {
                model: PricingInfo(**prices)
                for model, prices in models.items()
            }

        return PricingResponse(
            providers=providers,
            timestamp=datetime.utcnow(),
        )
    except Exception as e:
        request_id = getattr(http_request.state, 'request_id', None)
        raise_secure_http_exception(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error=e,
            public_message="Failed to retrieve pricing information",
            log_message="Pricing retrieval failed",
            request_id=request_id
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


# =============================================================================
# Tool Use Endpoints
# =============================================================================

@app.get("/v1/tools", tags=["tools"])
async def list_tools():
    """
    List all available tools and their definitions.

    Returns information about built-in tools (GitHub, system, weather)
    and their parameters for use with the tool execution endpoint.
    """
    return {
        "tools": tool_registry.get_tools_info(),
        "count": len(tool_registry.list_tools()),
        "available": tool_registry.list_tools(),
    }


@app.get("/v1/tools/{tool_name}", tags=["tools"])
async def get_tool_details(tool_name: str):
    """
    Get detailed information about a specific tool.

    - **tool_name**: Name of the tool (github, system, weather)

    Returns the tool's definition including parameters and requirements.
    """
    tool = tool_registry.get(tool_name)
    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool '{tool_name}' not found"
        )

    definition = tool.definition
    return {
        "name": definition.name,
        "description": definition.description,
        "parameters": [
            {
                "name": p.name,
                "type": p.type,
                "description": p.description,
                "required": p.required,
                "default": p.default,
                "enum": p.enum,
            }
            for p in definition.parameters
        ],
        "requires_confirmation": definition.requires_confirmation,
        "dangerous": definition.dangerous,
    }


@app.post("/v1/tools/execute", tags=["tools"])
async def execute_tool(request: Request, http_request: Request):
    """
    Execute a tool with the provided parameters.

    **Request body:**
    ```json
    {
        "tool": "github",
        "params": {
            "action": "list_repos"
        }
    }
    ```

    **Available tools:**
    - `github` - GitHub API integration (requires GITHUB_TOKEN)
    - `system` - System commands and information
    - `weather` - Weather data via Open-Meteo API

    Returns the tool execution result or error.
    """
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON body"
        )

    tool_name = data.get("tool")
    params = data.get("params", {})

    if not tool_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="'tool' is required"
        )

    start_time = time.time()

    try:
        result = await tool_registry.execute(tool_name, params)

        # Track metrics
        duration_ms = (time.time() - start_time) * 1000
        prom_metrics.track_request("POST", "/v1/tools/execute", 200 if result.success else 500, duration_ms)

        return {
            "success": result.success,
            "data": result.data,
            "error": result.error,
            "timestamp": result.timestamp.isoformat(),
            "execution_time_ms": round(duration_ms, 2),
        }

    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        prom_metrics.track_request("POST", "/v1/tools/execute", 500, duration_ms)

        request_id = getattr(http_request.state, 'request_id', None)
        raise_secure_http_exception(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error=e,
            public_message="Tool execution failed",
            log_message=f"Tool execution failed for: {tool_name}",
            request_id=request_id
        )


@app.get("/v1/tools/definitions/openai", tags=["tools"])
async def get_openai_tool_definitions():
    """
    Get tool definitions in OpenAI function calling format.

    Returns tools formatted for use with OpenAI's function calling API.
    This can be passed directly to the OpenAI API's `tools` parameter.
    """
    return {
        "tools": tool_registry.get_definitions(),
        "count": len(tool_registry.list_tools()),
    }
