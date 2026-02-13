"""Middleware for MasterClaw Core API

Includes rate limiting, request logging, and security headers
"""

import time
import logging
from typing import Callable
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


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log all requests with timing"""
    
    async def dispatch(self, request: Request, call_next: Callable):
        start_time = time.time()
        
        # Log request
        logger.info(f"→ {request.method} {request.url.path}")
        
        # Process request
        try:
            response = await call_next(request)
        except Exception as e:
            logger.error(f"✗ {request.method} {request.url.path} - Error: {str(e)}")
            return JSONResponse(
                status_code=500,
                content={"error": "Internal server error"}
            )
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Log response
        status_icon = "✓" if response.status_code < 400 else "✗"
        logger.info(
            f"{status_icon} {request.method} {request.url.path} "
            f"- {response.status_code} - {duration:.3f}s"
        )
        
        # Add timing header
        response.headers["X-Response-Time"] = f"{duration:.3f}s"
        
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
    """Decorator to require API key for endpoint"""
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
        
        # Get API key from header
        api_key = request.headers.get("X-API-Key")
        expected_key = request.app.state.api_key if hasattr(request.app.state, 'api_key') else None
        
        if expected_key and api_key != expected_key:
            logger.warning(f"Invalid API key from {request.client.host}")
            return JSONResponse(
                status_code=401,
                content={"error": "Invalid or missing API key"}
            )
        
        return await func(*args, **kwargs)
    
    return wrapper
