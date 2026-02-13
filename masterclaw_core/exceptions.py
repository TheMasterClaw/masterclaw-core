"""Error handling and custom exceptions"""

from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException


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
    import logging
    logger = logging.getLogger("masterclaw")
    logger.exception("Unhandled exception")
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc) if __debug__ else "An unexpected error occurred",
        }
    )
