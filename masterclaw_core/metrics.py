"""Prometheus metrics for MasterClaw Core"""

from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

# Request metrics
http_requests_total = Counter(
    'masterclaw_http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)

http_request_duration_seconds = Histogram(
    'masterclaw_http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

# Chat metrics
chat_requests_total = Counter(
    'masterclaw_chat_requests_total',
    'Total chat requests',
    ['provider', 'model']
)

chat_tokens_total = Counter(
    'masterclaw_chat_tokens_total',
    'Total tokens used in chat',
    ['provider', 'model']
)

# Memory metrics
memory_operations_total = Counter(
    'masterclaw_memory_operations_total',
    'Total memory operations',
    ['operation', 'status']
)

memory_search_duration_seconds = Histogram(
    'masterclaw_memory_search_duration_seconds',
    'Memory search duration in seconds'
)

# System metrics
active_sessions = Gauge(
    'masterclaw_active_sessions',
    'Number of active sessions'
)

memory_entries_total = Gauge(
    'masterclaw_memory_entries_total',
    'Total number of memory entries'
)

# LLM provider metrics
llm_requests_total = Counter(
    'masterclaw_llm_requests_total',
    'Total LLM API requests',
    ['provider', 'status']
)

llm_request_duration_seconds = Histogram(
    'masterclaw_llm_request_duration_seconds',
    'LLM request duration in seconds',
    ['provider']
)


def track_request(method: str, endpoint: str, status_code: int, duration_ms: float):
    """Track an HTTP request"""
    http_requests_total.labels(
        method=method,
        endpoint=endpoint,
        status_code=str(status_code)
    ).inc()
    http_request_duration_seconds.labels(
        method=method,
        endpoint=endpoint
    ).observe(duration_ms / 1000)


def track_chat(provider: str, model: str, tokens: int):
    """Track a chat request"""
    chat_requests_total.labels(provider=provider, model=model).inc()
    if tokens > 0:
        chat_tokens_total.labels(provider=provider, model=model).inc(tokens)


def track_memory_operation(operation: str, success: bool = True):
    """Track a memory operation"""
    status = 'success' if success else 'error'
    memory_operations_total.labels(operation=operation, status=status).inc()


def track_memory_search(duration_ms: float):
    """Track memory search duration"""
    memory_search_duration_seconds.observe(duration_ms / 1000)


def track_llm_request(provider: str, duration_ms: float, success: bool = True):
    """Track an LLM API request"""
    status = 'success' if success else 'error'
    llm_requests_total.labels(provider=provider, status=status).inc()
    llm_request_duration_seconds.labels(provider=provider).observe(duration_ms / 1000)


def update_active_sessions(count: int):
    """Update active sessions gauge"""
    active_sessions.set(count)


def update_memory_entries(count: int):
    """Update memory entries gauge"""
    memory_entries_total.set(count)


def get_metrics_response() -> Response:
    """Generate Prometheus metrics response"""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )
