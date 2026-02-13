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
    r"(--)|(;)|(/\*)|(\*/)|(@@)|(\bOR\b\s+\d+\s*=\s*\d+)|(\bAND\b\s+\d+\s*=\s*\d+)",
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
    """Simple in-memory rate limiting"""
    
    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests = {}  # ip -> [(timestamp, count)]
    
    async def dispatch(self, request: Request, call_next: Callable):
        # Get client IP
        client_ip = request.headers.get("X-Forwarded-For", request.client.host)
        
        # Clean old requests
        current_time = time.time()
        window_start = current_time - 60  # 1 minute window
        
        if client_ip in self.requests:
            self.requests[client_ip] = [
                req for req in self.requests[client_ip]
                if req[0] > window_start
            ]
        
        # Count requests in window
        request_count = sum(
            count for ts, count in self.requests.get(client_ip, [])
        )
        
        if request_count >= self.requests_per_minute:
            logger.warning(f"Rate limit exceeded for {client_ip}")
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "limit": self.requests_per_minute,
                    "window": "1 minute"
                }
            )
        
        # Record request
        if client_ip not in self.requests:
            self.requests[client_ip] = []
        self.requests[client_ip].append((current_time, 1))
        
        # Add rate limit headers
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(
            max(0, self.requests_per_minute - request_count - 1)
        )
        
        return response


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
    """Decorator to require API key for endpoint with timing attack protection"""
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
        
        # Get API key from header with input sanitization
        api_key_header = request.headers.get("X-API-Key", "")
        try:
            api_key = sanitize_input(api_key_header, max_length=256)
        except ValueError as e:
            logger.warning(f"[{request_id}] Rejected API key with suspicious content")
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
            client_ip = request.headers.get("X-Forwarded-For", request.client.host if request.client else "unknown")
            logger.warning(f"[{request_id}] Invalid API key attempt from {client_ip}")
            return JSONResponse(
                status_code=401,
                content={"error": "Invalid or missing API key"}
            )
        
        return await func(*args, **kwargs)
    
    return wrapper
