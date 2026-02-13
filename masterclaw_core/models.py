"""Pydantic models for MasterClaw Core"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime


class ChatRequest(BaseModel):
    """Request model for chat completions"""
    message: str = Field(..., description="User message", min_length=1)
    session_id: Optional[str] = Field(None, description="Session identifier for context")
    model: Optional[str] = Field(None, description="LLM model to use")
    provider: Optional[Literal["openai", "anthropic"]] = Field(None, description="LLM provider")
    temperature: float = Field(0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, ge=1, le=4096)
    system_prompt: Optional[str] = Field(None, description="Custom system prompt")
    use_memory: bool = Field(True, description="Whether to use memory retrieval")


class ChatResponse(BaseModel):
    """Response model for chat completions"""
    response: str = Field(..., description="AI response")
    model: str = Field(..., description="Model used")
    provider: str = Field(..., description="Provider used")
    session_id: Optional[str] = Field(None, description="Session identifier")
    tokens_used: Optional[int] = Field(None, description="Total tokens used")
    memories_used: int = Field(0, description="Number of memories retrieved")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class MemoryEntry(BaseModel):
    """Model for memory entries"""
    id: Optional[str] = Field(None, description="Memory ID")
    content: str = Field(..., description="Memory content", min_length=1)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    source: Optional[str] = Field(None, description="Source of memory")


class MemorySearchRequest(BaseModel):
    """Request model for memory search"""
    query: str = Field(..., description="Search query", min_length=1)
    top_k: int = Field(5, ge=1, le=20, description="Number of results")
    filter_metadata: Optional[Dict[str, Any]] = Field(None, description="Metadata filters")


class MemorySearchResponse(BaseModel):
    """Response model for memory search"""
    query: str = Field(..., description="Original query")
    results: List[MemoryEntry] = Field(default_factory=list)
    total_results: int = Field(0, description="Total matching results")


class HealthResponse(BaseModel):
    """Health check response"""
    status: str = Field("healthy", description="Service status")
    version: str = Field(..., description="API version")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    services: Dict[str, str] = Field(default_factory=dict, description="Service statuses")


class ToolRequest(BaseModel):
    """Request model for tool execution"""
    tool: str = Field(..., description="Tool name")
    action: str = Field(..., description="Action to perform")
    params: Dict[str, Any] = Field(default_factory=dict, description="Tool parameters")


class ToolResponse(BaseModel):
    """Response model for tool execution"""
    success: bool = Field(..., description="Whether the tool executed successfully")
    result: Any = Field(None, description="Tool result")
    error: Optional[str] = Field(None, description="Error message if failed")


class AnalyticsStatsRequest(BaseModel):
    """Request model for analytics stats"""
    days: int = Field(7, ge=1, le=90, description="Number of days to look back")


class AnalyticsStatsResponse(BaseModel):
    """Response model for analytics statistics"""
    period_days: int = Field(..., description="Period in days")
    total_requests: int = Field(..., description="Total API requests")
    avg_response_time_ms: float = Field(..., description="Average response time")
    total_chats: int = Field(..., description="Total chat interactions")
    total_tokens: int = Field(..., description="Total tokens used")
    provider_usage: Dict[str, int] = Field(default_factory=dict, description="Usage by provider")
    error_rate: float = Field(..., description="Error rate (0-1)")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AnalyticsSummaryResponse(BaseModel):
    """High-level analytics summary"""
    status: str = Field("available", description="Analytics status")
    tracked_metrics: List[str] = Field(default_factory=list, description="Available metrics")
    endpoints: List[str] = Field(default_factory=list, description="Analytics endpoints")
    retention_days: int = Field(30, description="Data retention period")


# =============================================================================
# Session Management Models
# =============================================================================

class SessionInfo(BaseModel):
    """Information about a chat session"""
    session_id: str = Field(..., description="Unique session identifier")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Session creation time")
    last_active: datetime = Field(default_factory=datetime.utcnow, description="Last activity timestamp")
    message_count: int = Field(0, description="Number of messages in session")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Session metadata")


class SessionListResponse(BaseModel):
    """Response for listing sessions"""
    sessions: List[SessionInfo] = Field(default_factory=list, description="List of sessions")
    total: int = Field(0, description="Total number of sessions")
    limit: int = Field(100, description="Max sessions returned")
    offset: int = Field(0, description="Pagination offset")


class SessionHistoryResponse(BaseModel):
    """Response for session chat history"""
    session_id: str = Field(..., description="Session identifier")
    messages: List[MemoryEntry] = Field(default_factory=list, description="Chat messages in session")
    total_messages: int = Field(0, description="Total message count")
    session_duration_minutes: Optional[float] = Field(None, description="Session duration in minutes")


class SessionDeleteResponse(BaseModel):
    """Response for session deletion"""
    success: bool = Field(..., description="Whether deletion succeeded")
    session_id: str = Field(..., description="Deleted session ID")
    memories_deleted: int = Field(0, description="Number of associated memories deleted")
    message: str = Field(..., description="Status message")


class PaginationParams(BaseModel):
    """
    Validated pagination parameters for list endpoints.
    
    Prevents abuse via excessive limit values or negative offsets.
    """
    limit: int = Field(
        100,
        ge=1,
        le=500,
        description="Maximum number of items to return (1-500)"
    )
    offset: int = Field(
        0,
        ge=0,
        description="Pagination offset (must be non-negative)"
    )


class SessionHistoryParams(BaseModel):
    """
    Validated parameters for session history endpoint.
    
    Enforces reasonable limits to prevent memory exhaustion from
    retrieving excessive message history.
    """
    limit: int = Field(
        50,
        ge=1,
        le=100,
        description="Maximum messages to return (1-100)"
    )
    offset: int = Field(
        0,
        ge=0,
        description="Pagination offset (must be non-negative)"
    )
