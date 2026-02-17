"""Middleware for MasterClaw Core API

Includes rate limiting, request logging, security headers, and input validation
"""

import time
import logging
import hmac
import re
import uuid
from typing import Callable, Optional
from functools import wraps

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .audit_logger import audit_logger, SecuritySeverity


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("masterclaw")


# =============================================================================
# Input Sanitization Utilities
# =============================================================================

# Regex patterns for common injection attacks
SQL_INJECTION_PATTERN = re.compile(
    r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE|UNION|DECLARE|CAST)\b)|"
    r"(--)|(;)|(/\*)|(\*/)|(@@)|"
    r"(\bOR\b\s+['\"]?\d+['\"]?\s*=\s*['\"]?\d+['\"]?)|"
    r"(\bAND\b\s+['\"]?\d+['\"]?\s*=\s*['\"]?\d+['\"]?)|"
    r"('\s*OR\s+'?\d)|('\s*AND\s+'?\d)|"
    r"(\bOR\b\s*['\"]\w+['\"]\s*=\s*['\"]\w+['\"])|"
    r"(\bWAITFOR\b\s+\bDELAY\b)|(\bBENCHMARK\b)|(\bSLEEP\b\s*\()",
    re.IGNORECASE
)

XSS_PATTERN = re.compile(
    r"(<script)|(javascript:)|(on\w+\s*=)|(<iframe)|(<object)|(<embed)|"
    r"(expression\()|(eval\()|(alert\()",
    re.IGNORECASE
)

PATH_TRAVERSAL_PATTERN = re.compile(r"\.\./|\.\.\\|%2e%2e%2f|%2e%2e/|%2e%2e\\")

def sanitize_input(value: str, max_length: int = 10000) -> str:
    """
    Sanitize user input to prevent injection attacks.
    
    Args:
        value: The input string to sanitize
        max_length: Maximum allowed length
        
    Returns:
        Sanitized string or raises ValueError if dangerous content detected
        
    Raises:
        ValueError: If potentially dangerous content is detected
    """
    if not isinstance(value, str):
        return value
    
    # Check length
    if len(value) > max_length:
        raise ValueError(f"Input exceeds maximum length of {max_length} characters")
    
    # Check for SQL injection patterns
    if SQL_INJECTION_PATTERN.search(value):
        raise ValueError("Potentially dangerous input detected")
    
    # Check for XSS patterns
    if XSS_PATTERN.search(value):
        raise ValueError("Potentially dangerous input detected")
    
    # Check for path traversal
    if PATH_TRAVERSAL_PATTERN.search(value):
        raise ValueError("Potentially dangerous input detected")
    
    return value

def safe_compare_keys(provided_key: Optional[str], expected_key: Optional[str]) -> bool:
    """
    Constant-time comparison of API keys to prevent timing attacks.
    
    Args:
        provided_key: The API key provided in the request
        expected_key: The expected API key
        
    Returns:
        True if keys match, False otherwise
    """
    if not provided_key or not expected_key:
        # Use hmac.compare_digest with dummy values to prevent timing leak
        return hmac.compare_digest("dummy", "dummy") and False
    
    # Ensure both are strings and encode to bytes
    provided = provided_key.encode('utf-8') if isinstance(provided_key, str) else b""
    expected = expected_key.encode('utf-8') if isinstance(expected_key, str) else b""
    
    return hmac.compare_digest(provided, expected)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log all requests with timing and request IDs for traceability"""
    
    async def dispatch(self, request: Request, call_next: Callable):
        # Generate or extract request ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
        request.state.request_id = request_id
        
        start_time = time.time()
        
        # Log request with request ID
        logger.info(f"[{request_id}] → {request.method} {request.url.path}")
        
        # Process request
        try:
            response = await call_next(request)
        except Exception as e:
            logger.error(f"[{request_id}] ✗ {request.method} {request.url.path} - Error: {str(e)}")
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "request_id": request_id
                }
            )
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Log response with request ID
        status_icon = "✓" if response.status_code < 400 else "✗"
        logger.info(
            f"[{request_id}] {status_icon} {request.method} {request.url.path} "
            f"- {response.status_code} - {duration:.3f}s"
        )
        
        # Add headers for debugging
        response.headers["X-Response-Time"] = f"{duration:.3f}s"
        response.headers["X-Request-ID"] = request_id
        
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Production-ready in-memory rate limiting with automatic cleanup.
    
    Features:
    - Configurable window size and request limits
    - Automatic cleanup of stale entries to prevent memory leaks
    - Per-IP tracking with X-Forwarded-For support
    - Thread-safe request counting
    """
    
    def __init__(
        self,
        app,
        requests_per_minute: int = 60,
        window_seconds: int = 60,
        max_ips_tracked: int = 10000,
        cleanup_interval: int = 1000
    ):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.window_seconds = window_seconds
        self.max_ips_tracked = max_ips_tracked
        self.cleanup_interval = cleanup_interval
        self.requests = {}  # ip -> [(timestamp, count)]
        self.request_count = 0  # Track requests for periodic cleanup
        self._lock = False  # Simple async-safe flag (actual locking not needed for GIL)
    
    def _cleanup_stale_entries(self, current_time: float):
        """Remove stale entries to prevent memory leaks."""
        window_start = current_time - self.window_seconds
        
        # Remove old requests for each IP
        ips_to_remove = []
        for ip, requests in self.requests.items():
            valid_requests = [
                req for req in requests
                if req[0] > window_start
            ]
            if valid_requests:
                self.requests[ip] = valid_requests
            else:
                ips_to_remove.append(ip)
        
        # Remove IPs with no active requests
        for ip in ips_to_remove:
            del self.requests[ip]
        
        # If still over max IPs, remove oldest entries
        if len(self.requests) > self.max_ips_tracked:
            # Sort by most recent request and keep top N
            sorted_ips = sorted(
                self.requests.items(),
                key=lambda x: max(req[0] for req in x[1]) if x[1] else 0,
                reverse=True
            )
            self.requests = dict(sorted_ips[:self.max_ips_tracked])
            logger.warning(
                f"Rate limiter hit max IPs tracked ({self.max_ips_tracked}), "
                f"removed {len(sorted_ips) - self.max_ips_tracked} oldest entries"
            )
    
    def _get_client_identifier(self, request: Request) -> str:
        """Get a unique identifier for the client."""
        # Use X-Forwarded-For if behind a proxy, fallback to client host
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP in the chain (closest to client)
            return forwarded_for.split(',')[0].strip()
        
        if request.client:
            return request.client.host
        
        return "unknown"
    
    async def dispatch(self, request: Request, call_next: Callable):
        # Get client identifier
        client_id = self._get_client_identifier(request)
        
        # Get request ID for logging
        request_id = getattr(request.state, 'request_id', 'unknown')
        
        # Clean old requests periodically
        current_time = time.time()
        self.request_count += 1
        
        if self.request_count >= self.cleanup_interval:
            self._cleanup_stale_entries(current_time)
            self.request_count = 0
        
        # Clean old requests for this specific client
        window_start = current_time - self.window_seconds
        if client_id in self.requests:
            self.requests[client_id] = [
                req for req in self.requests[client_id]
                if req[0] > window_start
            ]
        
        # Count requests in window
        request_count = sum(
            count for ts, count in self.requests.get(client_id, [])
        )
        
        # Check if rate limit exceeded
        if request_count >= self.requests_per_minute:
            logger.warning(
                f"[{request_id}] Rate limit exceeded for {client_id}: "
                f"{request_count}/{self.requests_per_minute} requests"
            )
            # Log security audit event for rate limiting
            audit_logger.rate_limit_exceeded(
                message=f"Rate limit exceeded: {request_count}/{self.requests_per_minute} requests",
                client_ip=client_id,
                request_id=request_id,
                resource=request.url.path,
                details={
                    "limit": self.requests_per_minute,
                    "window_seconds": self.window_seconds,
                    "current_requests": request_count,
                    "user_agent": request.headers.get("User-Agent")
                }
            )
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "code": "RATE_LIMIT_EXCEEDED",
                    "limit": self.requests_per_minute,
                    "window": f"{self.window_seconds} seconds",
                    "retry_after": self.window_seconds
                },
                headers={
                    "Retry-After": str(self.window_seconds),
                    "X-RateLimit-Limit": str(self.requests_per_minute),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(current_time + self.window_seconds))
                }
            )
        
        # Record request
        if client_id not in self.requests:
            self.requests[client_id] = []
        self.requests[client_id].append((current_time, 1))
        
        remaining = max(0, self.requests_per_minute - request_count - 1)
        reset_time = int(current_time + self.window_seconds)
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers to successful responses
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_time)
        
        return response
    
    def get_stats(self) -> dict:
        """Get current rate limiter statistics for monitoring."""
        current_time = time.time()
        window_start = current_time - self.window_seconds
        
        active_ips = 0
        total_active_requests = 0
        
        for requests in self.requests.values():
            active = [r for r in requests if r[0] > window_start]
            if active:
                active_ips += 1
                total_active_requests += sum(r[1] for r in active)
        
        return {
            "tracked_ips": len(self.requests),
            "active_ips": active_ips,
            "total_requests_in_window": total_active_requests,
            "window_seconds": self.window_seconds,
            "requests_per_minute": self.requests_per_minute,
            "max_ips_tracked": self.max_ips_tracked
        }


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""
    
    async def dispatch(self, request: Request, call_next: Callable):
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        
        return response


def require_api_key(func: Callable) -> Callable:
    """Decorator to require API key for endpoint with timing attack protection and audit logging"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Extract request from args/kwargs
        request = kwargs.get('request')
        if not request and args:
            request = args[0]
        
        if not request:
            return JSONResponse(
                status_code=500,
                content={"error": "Request not found"}
            )
        
        # Get request ID for logging
        request_id = getattr(request.state, 'request_id', 'unknown')
        
        # Get client IP for audit logging
        client_ip = request.headers.get("X-Forwarded-For", request.client.host if request.client else "unknown")
        user_agent = request.headers.get("User-Agent")
        
        # Get API key from header with input sanitization
        api_key_header = request.headers.get("X-API-Key", "")
        try:
            api_key = sanitize_input(api_key_header, max_length=256)
        except ValueError as e:
            logger.warning(f"[{request_id}] Rejected API key with suspicious content")
            # Log security audit event for suspicious API key
            audit_logger.input_validation_failed(
                message="API key rejected due to suspicious content (possible injection)",
                client_ip=client_ip.split(',')[0].strip() if ',' in client_ip else client_ip,
                request_id=request_id,
                user_agent=user_agent,
                resource=request.url.path,
                details={
                    "reason": "suspicious_content",
                    "field": "X-API-Key",
                    "error": str(e)
                },
                severity=SecuritySeverity.HIGH
            )
            return JSONResponse(
                status_code=401,
                content={"error": "Invalid API key format"}
            )
        
        # Get expected key from app state
        expected_key = None
        if hasattr(request.app.state, 'api_key'):
            expected_key = request.app.state.api_key
        
        # Use constant-time comparison to prevent timing attacks
        if expected_key and not safe_compare_keys(api_key, expected_key):
            logger.warning(f"[{request_id}] Invalid API key attempt from {client_ip}")
            # Log security audit event for failed authentication
            audit_logger.auth_failure(
                message="Invalid API key provided",
                client_ip=client_ip.split(',')[0].strip() if ',' in client_ip else client_ip,
                request_id=request_id,
                user_agent=user_agent,
                resource=request.url.path,
                details={
                    "reason": "invalid_key",
                    "has_key": bool(api_key),
                    "key_length": len(api_key) if api_key else 0
                },
                severity=SecuritySeverity.MEDIUM
            )
            return JSONResponse(
                status_code=401,
                content={"error": "Invalid or missing API key"}
            )
        
        return await func(*args, **kwargs)
    
    return wrapper
