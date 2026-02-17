"""Error handling and custom exceptions

Provides secure error handling that prevents sensitive information leakage
in production environments while preserving full debugging capabilities.
"""

import os
import logging
from functools import wraps
from typing import Callable, Optional, Any

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("masterclaw")


class MasterClawException(Exception):
    """Base exception for MasterClaw"""
    
    def __init__(self, message: str, status_code: int = 500, details: dict = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class MemoryNotFoundException(MasterClawException):
    """Raised when a memory is not found"""
    
    def __init__(self, memory_id: str):
        super().__init__(
            message=f"Memory not found: {memory_id}",
            status_code=404,
            details={"memory_id": memory_id}
        )


class LLMProviderException(MasterClawException):
    """Raised when LLM provider fails"""
    
    def __init__(self, provider: str, original_error: str):
        super().__init__(
            message=f"{provider} provider error: {original_error}",
            status_code=503,
            details={"provider": provider, "original_error": original_error}
        )


class RateLimitExceededException(MasterClawException):
    """Raised when rate limit is exceeded"""
    
    def __init__(self, retry_after: int = 60):
        super().__init__(
            message="Rate limit exceeded",
            status_code=429,
            details={"retry_after": retry_after}
        )


async def masterclaw_exception_handler(request: Request, exc: MasterClawException):
    """Handle custom exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.message,
            "details": exc.details,
            "type": exc.__class__.__name__,
        }
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors"""
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(x) for x in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
        })
    
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation error",
            "errors": errors,
        }
    )


async def general_exception_handler(request: Request, exc: Exception):
    """Handle all other exceptions"""
    logger.exception("Unhandled exception")
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc) if __debug__ else "An unexpected error occurred",
        }
    )


# =============================================================================
# Secure Error Handling Utilities
# =============================================================================

def is_production_environment() -> bool:
    """Check if running in production environment."""
    env = os.getenv("NODE_ENV", os.getenv("ENV", "development")).lower()
    return env in ("production", "prod")


def get_secure_error_message(
    error: Exception,
    default_message: str = "An unexpected error occurred",
    include_details: Optional[bool] = None
) -> str:
    """
    Get an error message that is safe to return to clients.
    
    In production, returns a generic message to prevent information leakage.
    In development, returns the actual error message for debugging.
    
    Args:
        error: The exception that occurred
        default_message: Generic message to use in production
        include_details: Override to force include/exclude details (default: auto-detect)
        
    Returns:
        Safe error message for client consumption
        
    Example:
        >>> try:
        ...     risky_operation()
        ... except Exception as e:
        ...     raise HTTPException(
        ...         status_code=500,
        ...         detail=get_secure_error_message(e, "Database query failed")
        ...     )
    """
    if include_details is None:
        include_details = not is_production_environment()
    
    if include_details or __debug__:
        return str(error)
    
    return default_message


def raise_secure_http_exception(
    status_code: int,
    error: Exception,
    public_message: str,
    log_message: Optional[str] = None,
    request_id: Optional[str] = None
) -> None:
    """
    Raise an HTTPException with a secure error message.
    
    Logs full error details for debugging but only exposes safe
    information to the client.
    
    Args:
        status_code: HTTP status code
        error: The actual exception that occurred
        public_message: Safe message to return to client
        log_message: Additional context for logs (optional)
        request_id: Request ID for log correlation (optional)
        
    Raises:
        HTTPException: With secure error details
        
    Example:
        >>> try:
        ...     db.query(user_input)
        ... except DatabaseError as e:
        ...     raise_secure_http_exception(
        ...         status_code=500,
        ...         error=e,
        ...         public_message="Failed to retrieve data",
        ...         log_message="Database query failed for user search",
        ...         request_id=request.state.request_id
        ...     )
    """
    # Log full error details for debugging
    req_ctx = f" [req:{request_id}]" if request_id else ""
    log_ctx = f" - {log_message}" if log_message else ""
    logger.error(
        f"HTTP {status_code} error{req_ctx}{log_ctx}: {type(error).__name__}: {error}",
        exc_info=True
    )
    
    # Raise with secure message
    raise HTTPException(
        status_code=status_code,
        detail=get_secure_error_message(error, public_message)
    )


def secure_endpoint(handler: Callable) -> Callable:
    """
    Decorator to wrap endpoint handlers with secure error handling.
    
    Catches all unhandled exceptions and returns safe error responses
    that don't leak internal implementation details.
    
    Args:
        handler: The endpoint handler function to wrap
        
    Returns:
        Wrapped handler with secure error handling
        
    Example:
        >>> @secure_endpoint
        ... async def my_endpoint(request: Request):
        ...     result = await risky_operation()
        ...     return {"data": result}
    """
    @wraps(handler)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        # Extract request for logging context
        request: Optional[Request] = None
        for arg in args:
            if isinstance(arg, Request):
                request = arg
                break
        if not request:
            request = kwargs.get('request') or kwargs.get('http_request')
        
        request_id = getattr(request.state, 'request_id', None) if request else None
        req_ctx = f" [req:{request_id}]" if request_id else ""
        
        try:
            return await handler(*args, **kwargs)
        except HTTPException:
            # Re-raise HTTPExceptions as-is
            raise
        except Exception as e:
            # Log full error details
            endpoint_name = handler.__name__
            logger.exception(
                f"Unhandled exception in {endpoint_name}{req_ctx}: {type(e).__name__}: {e}"
            )
            
            # Return safe error response
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=get_secure_error_message(
                    e, 
                    "An unexpected error occurred while processing your request"
                )
            )
    
    return wrapper
