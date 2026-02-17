"""Structured JSON logging for MasterClaw Core

Provides production-ready structured logging with:
- JSON output format for log aggregation systems (Loki, ELK, etc.)
- Request context correlation for distributed tracing
- Automatic log level routing based on severity
- Context variables that follow execution flow

Usage:
    from masterclaw_core.structured_logger import get_logger, request_context
    
    # In request handlers
    with request_context(request_id="abc123", user_id="user456"):
        logger = get_logger("masterclaw.chat")
        logger.info("Processing chat request", extra={"model": "gpt-4"})
        # Output: {"timestamp": "...", "level": "INFO", "message": "...", 
        #          "request_id": "abc123", "user_id": "user456", "model": "gpt-4"}
"""

import json
import logging
import sys
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Union
from functools import wraps


# Context variables for request correlation
_request_id: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
_session_id: ContextVar[Optional[str]] = ContextVar('session_id', default=None)
_user_id: ContextVar[Optional[str]] = ContextVar('user_id', default=None)
_client_ip: ContextVar[Optional[str]] = ContextVar('client_ip', default=None)


class StructuredLogRecord(logging.LogRecord):
    """Extended log record with structured data support"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.structured_data = {}


class JSONFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.
    
    Outputs logs as JSON for easy parsing by log aggregation systems.
    Includes standard fields plus any extra context data.
    
    Example output:
        {
            "timestamp": "2026-02-17T16:45:00.123Z",
            "level": "INFO",
            "logger": "masterclaw.chat",
            "message": "Chat request processed",
            "request_id": "abc123",
            "session_id": "sess456",
            "duration_ms": 123.45,
            "extra": {"model": "gpt-4", "tokens": 150}
        }
    """
    
    def __init__(
        self,
        include_context: bool = True,
        flatten_extra: bool = False,
        timestamp_format: str = "iso"
    ):
        super().__init__()
        self.include_context = include_context
        self.flatten_extra = flatten_extra
        self.timestamp_format = timestamp_format
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_data: Dict[str, Any] = {
            "timestamp": self._format_timestamp(record.created),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add source location for debugging
        if record.levelno >= logging.WARNING:
            log_data["source"] = {
                "file": record.pathname,
                "line": record.lineno,
                "function": record.funcName,
            }
        
        # Add context variables if enabled
        if self.include_context:
            context = self._get_context()
            if context:
                log_data.update(context)
        
        # Add structured extra data
        extra_data = self._extract_extra_data(record)
        if extra_data:
            if self.flatten_extra:
                log_data.update(extra_data)
            else:
                log_data["extra"] = extra_data
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self._format_exception(record.exc_info)
        
        return json.dumps(log_data, default=str)
    
    def _format_timestamp(self, timestamp: float) -> str:
        """Format timestamp according to configured format"""
        dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        if self.timestamp_format == "iso":
            return dt.isoformat().replace("+00:00", "Z")
        return dt.strftime(self.timestamp_format)
    
    def _get_context(self) -> Dict[str, Any]:
        """Get context variables"""
        context = {}
        req_id = _request_id.get()
        if req_id:
            context["request_id"] = req_id
        sess_id = _session_id.get()
        if sess_id:
            context["session_id"] = sess_id
        usr_id = _user_id.get()
        if usr_id:
            context["user_id"] = usr_id
        ip = _client_ip.get()
        if ip:
            context["client_ip"] = ip
        return context
    
    def _extract_extra_data(self, record: logging.LogRecord) -> Dict[str, Any]:
        """Extract extra fields from log record"""
        # Standard logging fields to exclude
        standard_fields = {
            'name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
            'filename', 'module', 'exc_info', 'exc_text', 'stack_info',
            'lineno', 'funcName', 'created', 'msecs', 'relativeCreated',
            'thread', 'threadName', 'processName', 'process', 'message',
            'asctime', 'structured_data'
        }
        
        extra = {}
        for key, value in record.__dict__.items():
            if key not in standard_fields and not key.startswith('_'):
                extra[key] = value
        
        # Also check for structured_data attribute
        if hasattr(record, 'structured_data'):
            extra.update(record.structured_data)
        
        return extra
    
    def _format_exception(self, exc_info) -> Dict[str, str]:
        """Format exception information"""
        import traceback
        return {
            "type": exc_info[0].__name__ if exc_info[0] else None,
            "message": str(exc_info[1]) if exc_info[1] else None,
            "traceback": traceback.format_exception(*exc_info) if exc_info else None,
        }


class ConsoleFormatter(logging.Formatter):
    """
    Human-readable console formatter for development.
    
    Provides colored output and readable formatting for local development.
    """
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m',
    }
    
    def __init__(self, use_colors: bool = True, include_context: bool = True):
        super().__init__(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self.use_colors = use_colors and sys.stdout.isatty()
        self.include_context = include_context
    
    def format(self, record: logging.LogRecord) -> str:
        """Format with optional colors and context"""
        # Get base formatted message
        message = super().format(record)
        
        # Add context info
        if self.include_context:
            context_parts = []
            req_id = _request_id.get()
            if req_id:
                context_parts.append(f"req:{req_id}")
            sess_id = _session_id.get()
            if sess_id:
                context_parts.append(f"sess:{sess_id}")
            
            if context_parts:
                context_str = " [" + ", ".join(context_parts) + "]"
                # Insert context before the message
                parts = message.rsplit(' - ', 1)
                if len(parts) == 2:
                    message = f"{parts[0]}{context_str} - {parts[1]}"
        
        # Add colors
        if self.use_colors:
            color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
            message = f"{color}{message}{self.COLORS['RESET']}"
        
        return message


class StructuredLogger:
    """
    Wrapper around standard logger with structured logging support.
    
    Provides convenient methods for logging with structured data and
    automatically includes context variables.
    
    Example:
        logger = StructuredLogger("masterclaw.chat")
        logger.info("Request processed", model="gpt-4", tokens=150, duration_ms=123.45)
    """
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.name = name
    
    def _log(
        self,
        level: int,
        message: str,
        extra: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """Internal log method with structured data support"""
        # Merge extra dict with kwargs
        structured_data = {}
        if extra:
            structured_data.update(extra)
        structured_data.update(kwargs)
        
        # Create log record with structured data
        record = self.logger.makeRecord(
            self.name, level, "(unknown file)", 0, message, (), None
        )
        
        # Add structured data to record
        for key, value in structured_data.items():
            setattr(record, key, value)
        
        self.logger.handle(record)
    
    def debug(self, message: str, **kwargs):
        """Log debug message with structured data"""
        self._log(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message with structured data"""
        self._log(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message with structured data"""
        self._log(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message with structured data"""
        self._log(logging.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message with structured data"""
        self._log(logging.CRITICAL, message, **kwargs)
    
    def exception(self, message: str, **kwargs):
        """Log exception with structured data"""
        kwargs['exc_info'] = True
        self._log(logging.ERROR, message, **kwargs)
    
    def log_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        **kwargs
    ):
        """Log HTTP request with standard fields"""
        level = logging.INFO if status_code < 400 else logging.WARNING
        if status_code >= 500:
            level = logging.ERROR
        
        self._log(
            level,
            f"{method} {path} - {status_code}",
            method=method,
            path=path,
            status_code=status_code,
            duration_ms=round(duration_ms, 2),
            **kwargs
        )
    
    def log_chat(
        self,
        provider: str,
        model: str,
        tokens_used: int,
        duration_ms: float,
        **kwargs
    ):
        """Log chat completion with standard fields"""
        self._log(
            logging.INFO,
            f"Chat completion: {provider}/{model}",
            provider=provider,
            model=model,
            tokens_used=tokens_used,
            duration_ms=round(duration_ms, 2),
            **kwargs
        )


# =============================================================================
# Context Management
# =============================================================================

class request_context:
    """
    Context manager for setting request correlation context.
    
    Automatically sets and clears context variables for the duration
    of the request, ensuring proper isolation between concurrent requests.
    
    Usage:
        async def handle_request(request: Request):
            with request_context(
                request_id=request.headers.get("X-Request-ID", str(uuid.uuid4())),
                session_id=request.session_id,
                client_ip=request.client.host
            ):
                # All logs within this block include context
                logger.info("Processing request")
                await process()
    
    Or as a decorator:
        @request_context.inject
        async def my_handler(request_id: str = None):
            logger.info("This has context")
    """
    
    def __init__(
        self,
        request_id: Optional[str] = None,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        client_ip: Optional[str] = None
    ):
        self.request_id = request_id or str(uuid.uuid4())[:8]
        self.session_id = session_id
        self.user_id = user_id
        self.client_ip = client_ip
        self.tokens = []
    
    def __enter__(self):
        """Set context variables"""
        self.tokens.append(_request_id.set(self.request_id))
        if self.session_id:
            self.tokens.append(_session_id.set(self.session_id))
        if self.user_id:
            self.tokens.append(_user_id.set(self.user_id))
        if self.client_ip:
            self.tokens.append(_client_ip.set(self.client_ip))
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clear context variables"""
        for token in self.tokens:
            try:
                if token is not None:
                    # Get which context var this token belongs to
                    for var in [_request_id, _session_id, _user_id, _client_ip]:
                        try:
                            var.reset(token)
                            break
                        except ValueError:
                            continue
            except Exception:
                pass  # Best effort cleanup
    
    @classmethod
    def inject(cls, func):
        """Decorator to inject request context from function arguments"""
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            request_id = kwargs.get('request_id') or str(uuid.uuid4())[:8]
            session_id = kwargs.get('session_id')
            user_id = kwargs.get('user_id')
            client_ip = kwargs.get('client_ip')
            
            with cls(request_id=request_id, session_id=session_id, 
                     user_id=user_id, client_ip=client_ip):
                return await func(*args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            request_id = kwargs.get('request_id') or str(uuid.uuid4())[:8]
            session_id = kwargs.get('session_id')
            user_id = kwargs.get('user_id')
            client_ip = kwargs.get('client_ip')
            
            with cls(request_id=request_id, session_id=session_id,
                     user_id=user_id, client_ip=client_ip):
                return func(*args, **kwargs)
        
        # Return appropriate wrapper based on function type
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper


# =============================================================================
# Convenience Functions
# =============================================================================

def get_logger(name: str) -> StructuredLogger:
    """Get a structured logger instance"""
    return StructuredLogger(name)


def configure_logging(
    level: Union[int, str] = logging.INFO,
    json_format: bool = False,
    include_context: bool = True
):
    """
    Configure root logging with structured formatters.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: Use JSON formatter for production (True) or console for development (False)
        include_context: Include request context in logs
    """
    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)
    
    # Remove existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    
    # Set formatter
    if json_format:
        formatter = JSONFormatter(include_context=include_context)
    else:
        formatter = ConsoleFormatter(include_context=include_context)
    
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    root_logger.setLevel(level)
    
    # Set levels for specific loggers to reduce noise
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)


def get_current_context() -> Dict[str, Optional[str]]:
    """Get current request context for debugging"""
    return {
        "request_id": _request_id.get(),
        "session_id": _session_id.get(),
        "user_id": _user_id.get(),
        "client_ip": _client_ip.get(),
    }


# Global structured logger for masterclaw
structured_logger = get_logger("masterclaw")
