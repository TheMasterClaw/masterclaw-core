"""Request Deduplication Middleware for MasterClaw Core

Prevents redundant processing of identical concurrent requests by coalescing
them into a single execution. Particularly valuable for expensive operations
like LLM calls and memory searches.

Features:
- Automatic deduplication based on request signature (method + path + body + key headers)
- Configurable TTL for deduplication windows
- Per-endpoint enablement/disablement
- Prometheus metrics for cache hits/misses
- Automatic cleanup of completed requests
"""

import time
import hashlib
import json
import asyncio
from typing import Dict, Optional, Set, Callable, Any
from dataclasses import dataclass, field
from functools import wraps
from contextlib import asynccontextmanager

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from . import metrics as prom_metrics


@dataclass
class PendingRequest:
    """Represents a request currently being processed"""
    signature: str
    started_at: float
    event: asyncio.Event = field(default_factory=asyncio.Event)
    response: Optional[Response] = None
    error: Optional[Exception] = None
    waiters: int = 0


class RequestDeduplicationMiddleware(BaseHTTPMiddleware):
    """
    Middleware that deduplicates identical concurrent requests.
    
    When multiple identical requests arrive simultaneously, only one is processed
    and the result is shared with all waiting requests. This dramatically reduces
    load for expensive operations like LLM calls and memory searches.
    
    Usage:
        # Enable globally with default settings
        app.add_middleware(RequestDeduplicationMiddleware)
        
        # Or with custom configuration
        app.add_middleware(
            RequestDeduplicationMiddleware,
            ttl_seconds=5.0,
            max_pending=1000,
            enabled_paths={"/v1/chat", "/v1/memory/search"},
            excluded_paths={"/v1/health", "/metrics"}
        )
    
    Configuration Options:
        ttl_seconds: How long to wait for duplicate requests (default: 5.0)
        max_pending: Maximum number of pending requests to track (default: 1000)
        enabled_paths: Set of paths to enable deduplication for (default: all)
        excluded_paths: Set of paths to exclude (default: health, metrics)
        key_headers: Headers to include in request signature (default: content-type, accept)
    """
    
    def __init__(
        self,
        app,
        ttl_seconds: float = 5.0,
        max_pending: int = 1000,
        enabled_paths: Optional[Set[str]] = None,
        excluded_paths: Optional[Set[str]] = None,
        key_headers: Optional[Set[str]] = None,
    ):
        super().__init__(app)
        self.ttl_seconds = ttl_seconds
        self.max_pending = max_pending
        self.enabled_paths = enabled_paths
        self.excluded_paths = excluded_paths or {
            "/health", "/health/security", "/metrics", "/docs", "/redoc", "/openapi.json"
        }
        self.key_headers = key_headers or {"content-type", "accept", "x-api-key"}
        
        # Pending requests storage: signature -> PendingRequest
        self._pending: Dict[str, PendingRequest] = {}
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None
    
    async def startup(self):
        """Start background cleanup task"""
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    async def shutdown(self):
        """Stop background cleanup task"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
    
    async def _cleanup_loop(self):
        """Periodically clean up stale pending requests"""
        while True:
            try:
                await asyncio.sleep(self.ttl_seconds)
                await self._cleanup_stale_requests()
            except asyncio.CancelledError:
                break
            except Exception:
                # Log but don't crash the cleanup loop
                pass
    
    async def _cleanup_stale_requests(self):
        """Remove requests that have been pending too long"""
        now = time.time()
        stale_signatures = []
        
        async with self._lock:
            for signature, pending in self._pending.items():
                if now - pending.started_at > self.ttl_seconds * 2:
                    stale_signatures.append(signature)
            
            for signature in stale_signatures:
                pending = self._pending.pop(signature, None)
                if pending:
                    pending.error = TimeoutError("Request deduplication timeout")
                    pending.event.set()
    
    def _should_deduplicate(self, request: Request) -> bool:
        """Check if this request path should be deduplicated"""
        path = request.url.path
        
        # Always exclude certain paths
        if path in self.excluded_paths:
            return False
        
        # If enabled_paths is specified, only deduplicate those
        if self.enabled_paths is not None:
            # Support both exact matches and prefix matches
            for enabled_path in self.enabled_paths:
                if path == enabled_path or path.startswith(enabled_path + "/"):
                    return True
            return False
        
        # By default, only deduplicate POST/PUT/PATCH requests (not GET for caching)
        if request.method not in ("POST", "PUT", "PATCH"):
            return False
        
        return True
    
    async def _compute_signature(self, request: Request) -> str:
        """
        Compute a unique signature for this request.
        
        The signature includes:
        - HTTP method
        - Full URL path
        - Request body (for POST/PUT/PATCH)
        - Key headers (content-type, accept, api key)
        
        This ensures that requests with different parameters don't collide.
        """
        # Start with method and path
        components = [request.method, str(request.url.path)]
        
        # Add query parameters (sorted for consistency)
        query_params = sorted(request.query_params.items())
        if query_params:
            components.append(str(query_params))
        
        # Add key headers (case-insensitive header lookup)
        headers_dict = dict(request.headers)
        header_values = []
        for key in self.key_headers:
            # Try different case variations
            for header_key, header_value in headers_dict.items():
                if header_key.lower() == key.lower():
                    header_values.append(f"{key}:{header_value}")
                    break
        if header_values:
            components.append("|".join(sorted(header_values)))
        
        # Add request body for methods that typically have bodies
        if request.method in ("POST", "PUT", "PATCH") and request.headers.get("content-length"):
            try:
                # Read and restore body (can only be consumed once)
                body = await request.body()
                # Re-inject body so downstream can read it
                request._body = body
                components.append(body.decode("utf-8", errors="ignore"))
            except Exception:
                # If we can't read body, include a marker
                components.append("<body-unreadable>")
        
        # Create hash of all components
        signature_input = "|".join(components)
        return hashlib.sha256(signature_input.encode()).hexdigest()
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check if deduplication is enabled for this path
        if not self._should_deduplicate(request):
            return await call_next(request)
        
        # Compute request signature
        try:
            signature = await self._compute_signature(request)
        except Exception:
            # If signature computation fails, just process normally
            return await call_next(request)
        
        # Try to find or create pending request
        pending = None
        is_leader = False
        
        async with self._lock:
            # Check if there's already a pending request with this signature
            if signature in self._pending:
                pending = self._pending[signature]
                pending.waiters += 1
            else:
                # Create new pending request
                if len(self._pending) >= self.max_pending:
                    # Too many pending requests, process normally
                    return await call_next(request)
                
                pending = PendingRequest(
                    signature=signature,
                    started_at=time.time()
                )
                self._pending[signature] = pending
                is_leader = True
        
        if is_leader:
            # We're the leader - process the request
            try:
                response = await call_next(request)
                pending.response = response
                
                # Track metrics
                prom_metrics.track_deduplication(signature, "leader", pending.waiters)
                prom_metrics.update_deduplication_pending(len(self._pending))
                
            except Exception as e:
                pending.error = e
                raise
            finally:
                # Signal all waiters
                pending.event.set()
                
                # Remove from pending after a short delay to catch stragglers
                await asyncio.sleep(0.1)
                async with self._lock:
                    self._pending.pop(signature, None)
            
            return response
        
        else:
            # We're a follower - wait for the leader to complete
            try:
                await asyncio.wait_for(
                    pending.event.wait(),
                    timeout=self.ttl_seconds
                )
                
                # Track metrics
                prom_metrics.track_deduplication(signature, "follower", 0)
                prom_metrics.update_deduplication_pending(len(self._pending))
                
                if pending.error:
                    raise pending.error
                
                if pending.response is None:
                    # Shouldn't happen, but handle gracefully
                    return await call_next(request)
                
                # Return a copy of the response
                # Clone the response to avoid issues with streaming bodies
                return Response(
                    content=pending.response.body,
                    status_code=pending.response.status_code,
                    headers=dict(pending.response.headers),
                    media_type=pending.response.media_type,
                )
                
            except asyncio.TimeoutError:
                # Timeout waiting for leader, process ourselves
                async with self._lock:
                    pending.waiters -= 1
                
                prom_metrics.track_deduplication(signature, "timeout", 0)
                prom_metrics.update_deduplication_pending(len(self._pending))
                
                return await call_next(request)


def deduplicate(
    ttl_seconds: float = 5.0,
    key_func: Optional[Callable[..., str]] = None
):
    """
    Decorator to enable request deduplication for a specific endpoint.
    
    Usage:
        @app.post("/v1/expensive-operation")
        @deduplicate(ttl_seconds=10.0)
        async def expensive_operation(request: Request):
            # This will only execute once for concurrent identical requests
            return await do_expensive_work()
    
    Args:
        ttl_seconds: How long to deduplicate concurrent requests
        key_func: Optional function to extract deduplication key from arguments
                 (default: uses request body hash)
    """
    def decorator(func: Callable) -> Callable:
        # Storage for this endpoint's pending requests
        _pending: Dict[str, asyncio.Event] = {}
        _results: Dict[str, Any] = {}
        _lock = asyncio.Lock()
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Compute key
            if key_func:
                key = key_func(*args, **kwargs)
            else:
                # Default: use first argument (usually request) body hash
                request = args[0] if args else kwargs.get('request')
                if request and hasattr(request, 'body'):
                    try:
                        body = await request.body()
                        key = hashlib.sha256(body).hexdigest()
                    except Exception:
                        key = str(time.time())  # Fallback
                else:
                    key = str(time.time())
            
            async with _lock:
                if key in _pending:
                    event = _pending[key]
                    is_leader = False
                else:
                    event = asyncio.Event()
                    _pending[key] = event
                    is_leader = True
            
            if is_leader:
                try:
                    result = await func(*args, **kwargs)
                    _results[key] = result
                    return result
                except Exception as e:
                    _results[key] = e
                    raise
                finally:
                    event.set()
                    await asyncio.sleep(ttl_seconds)
                    async with _lock:
                        _pending.pop(key, None)
                        _results.pop(key, None)
            else:
                await event.wait()
                result = _results.get(key)
                if isinstance(result, Exception):
                    raise result
                return result
        
        return wrapper
    return decorator


class DeduplicationManager:
    """
    Manual deduplication control for complex use cases.
    
    Use this when you need fine-grained control over deduplication
    within endpoint handlers.
    
    Usage:
        dedup_manager = DeduplicationManager()
        
        @app.post("/v1/custom-operation")
        async def custom_operation(request: Request):
            key = f"custom:{request.client.host}:{hash_body(request)}"
            
            async with dedup_manager.acquire(key):
                # Only one request with this key executes at a time
                return await do_work()
    """
    
    def __init__(self, ttl_seconds: float = 5.0):
        self.ttl_seconds = ttl_seconds
        self._pending: Dict[str, asyncio.Event] = {}
        self._lock = asyncio.Lock()
    
    @asynccontextmanager
    async def acquire(self, key: str):
        """Async context manager for deduplicating by key"""
        event = None
        is_leader = False
        
        async with self._lock:
            if key in self._pending:
                event = self._pending[key]
            else:
                event = asyncio.Event()
                self._pending[key] = event
                is_leader = True
        
        if is_leader:
            try:
                yield self
            finally:
                event.set()
                await asyncio.sleep(self.ttl_seconds)
                async with self._lock:
                    self._pending.pop(key, None)
        else:
            # Wait for leader to complete before entering context
            await event.wait()
            yield None


# =============================================================================
# Singleton instance for application-wide use
# =============================================================================

_dedup_middleware_instance: Optional[RequestDeduplicationMiddleware] = None


def get_dedup_middleware() -> Optional[RequestDeduplicationMiddleware]:
    """Get the global deduplication middleware instance"""
    return _dedup_middleware_instance


def set_dedup_middleware(instance: RequestDeduplicationMiddleware):
    """Set the global deduplication middleware instance"""
    global _dedup_middleware_instance
    _dedup_middleware_instance = instance
