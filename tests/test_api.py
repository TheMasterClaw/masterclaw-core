import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException, Request
from unittest.mock import AsyncMock, patch, MagicMock

from masterclaw_core.main import app, lifespan
from masterclaw_core.models import ChatRequest, MemoryEntry, HealthResponse
from masterclaw_core.exceptions import (
    MasterClawException, MemoryNotFoundException, LLMProviderException,
    RateLimitExceededException, masterclaw_exception_handler,
    http_exception_handler, validation_exception_handler, general_exception_handler
)


# Create test client
client = TestClient(app)


class TestRootEndpoint:
    """Test the root endpoint"""
    
    def test_root_returns_status(self):
        """Test root endpoint returns basic info"""
        response = client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert data["name"] == "MasterClaw Core"
        assert "version" in data
        assert data["status"] == "running"
        assert "endpoints" in data


class TestHealthEndpoint:
    """Test the health check endpoint"""
    
    def test_health_check(self):
        """Test health endpoint returns service status"""
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "services" in data
        assert "memory" in data["services"]


class TestChatEndpoint:
    """Test the chat endpoint"""
    
    @patch("masterclaw_core.main.llm_router")
    @patch("masterclaw_core.main.memory")
    async def test_chat_basic(self, mock_memory, mock_llm):
        """Test basic chat functionality"""
        # Setup mocks
        mock_llm.chat = AsyncMock(return_value={
            "response": "Hello!",
            "model": "gpt-4",
            "provider": "openai"
        })
        mock_memory.search = AsyncMock(return_value=[])
        mock_memory.add = AsyncMock(return_value="memory-id")
        
        # Make request
        response = client.post("/v1/chat", json={
            "message": "Hi there!",
            "session_id": "test-session"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        
    def test_chat_missing_message(self):
        """Test chat requires message field"""
        response = client.post("/v1/chat", json={
            "session_id": "test"
        })
        assert response.status_code == 422  # Validation error
        
    def test_chat_empty_message(self):
        """Test chat rejects empty message"""
        response = client.post("/v1/chat", json={
            "message": "",
            "session_id": "test"
        })
        assert response.status_code == 422
        
    @patch("masterclaw_core.main.llm_router")
    async def test_chat_invalid_temperature(self, mock_llm):
        """Test chat validates temperature"""
        response = client.post("/v1/chat", json={
            "message": "Hi",
            "temperature": 5.0
        })
        assert response.status_code == 422


class TestMemoryEndpoints:
    """Test memory-related endpoints"""
    
    @patch("masterclaw_core.main.memory")
    async def test_add_memory(self, mock_memory):
        """Test adding a memory"""
        mock_memory.add = AsyncMock(return_value="test-memory-id")
        
        response = client.post("/v1/memory/add", json={
            "content": "Test memory content",
            "metadata": {"session_id": "abc"},
            "source": "test"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "memory_id" in data
        
    def test_add_memory_empty_content(self):
        """Test adding memory with empty content fails"""
        response = client.post("/v1/memory/add", json={
            "content": "",
            "source": "test"
        })
        assert response.status_code == 422
        
    @patch("masterclaw_core.main.memory")
    async def test_search_memory(self, mock_memory):
        """Test searching memories"""
        mock_memory.search = AsyncMock(return_value=[
            MemoryEntry(id="1", content="Result 1"),
            MemoryEntry(id="2", content="Result 2")
        ])
        
        response = client.post("/v1/memory/search", json={
            "query": "test query",
            "top_k": 5
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "test query"
        assert data["total_results"] == 2
        
    def test_search_memory_empty_query(self):
        """Test search with empty query fails"""
        response = client.post("/v1/memory/search", json={
            "query": ""
        })
        assert response.status_code == 422
        
    @patch("masterclaw_core.main.memory")
    async def test_get_memory(self, mock_memory):
        """Test getting a specific memory"""
        mock_memory.get = AsyncMock(return_value=MemoryEntry(
            id="test-id",
            content="Test content"
        ))
        
        response = client.get("/v1/memory/test-id")
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == "test-id"
        assert data["content"] == "Test content"
        
    @patch("masterclaw_core.main.memory")
    async def test_get_memory_not_found(self, mock_memory):
        """Test getting non-existent memory returns 404"""
        mock_memory.get = AsyncMock(return_value=None)
        
        response = client.get("/v1/memory/nonexistent")
        assert response.status_code == 404
        
    @patch("masterclaw_core.main.memory")
    async def test_delete_memory(self, mock_memory):
        """Test deleting a memory"""
        mock_memory.delete = AsyncMock(return_value=True)
        
        response = client.delete("/v1/memory/test-id")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        
    @patch("masterclaw_core.main.memory")
    async def test_delete_memory_not_found(self, mock_memory):
        """Test deleting non-existent memory returns 404"""
        mock_memory.delete = AsyncMock(return_value=False)
        
        response = client.delete("/v1/memory/nonexistent")
        assert response.status_code == 404


class TestExceptionHandlers:
    """Test custom exception handlers"""
    
    @pytest.mark.asyncio
    async def test_masterclaw_exception_handler(self):
        """Test handling of MasterClawException"""
        request = MagicMock(spec=Request)
        exc = MasterClawException(
            message="Test error",
            status_code=418,
            details={"foo": "bar"}
        )
        
        response = await masterclaw_exception_handler(request, exc)
        
        assert response.status_code == 418
        body = response.body.decode()
        assert "Test error" in body
        assert "MasterClawException" in body
        
    @pytest.mark.asyncio
    async def test_memory_not_found_exception(self):
        """Test MemoryNotFoundException formatting"""
        request = MagicMock(spec=Request)
        exc = MemoryNotFoundException("memory-123")
        
        response = await masterclaw_exception_handler(request, exc)
        
        assert response.status_code == 404
        body = response.body.decode()
        assert "memory-123" in body
        
    @pytest.mark.asyncio
    async def test_llm_provider_exception(self):
        """Test LLMProviderException formatting"""
        request = MagicMock(spec=Request)
        exc = LLMProviderException("openai", "API key invalid")
        
        response = await masterclaw_exception_handler(request, exc)
        
        assert response.status_code == 503
        body = response.body.decode()
        assert "openai" in body
        assert "API key invalid" in body
        
    @pytest.mark.asyncio
    async def test_rate_limit_exception(self):
        """Test RateLimitExceededException formatting"""
        request = MagicMock(spec=Request)
        exc = RateLimitExceededException(retry_after=120)
        
        response = await masterclaw_exception_handler(request, exc)
        
        assert response.status_code == 429
        body = response.body.decode()
        assert "Rate limit" in body


class TestMiddlewareIntegration:
    """Test middleware integration in the main app"""
    
    def test_security_headers_present(self):
        """Test that security headers are added by SecurityHeadersMiddleware"""
        response = client.get("/")
        
        assert response.status_code == 200
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["X-XSS-Protection"] == "1; mode=block"
        assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
        assert "default-src 'self'" in response.headers["Content-Security-Policy"]
    
    def test_request_logging_headers(self):
        """Test that request logging middleware adds timing header"""
        response = client.get("/")
        
        assert response.status_code == 200
        assert "X-Response-Time" in response.headers
        # Verify it's a valid time format
        time_str = response.headers["X-Response-Time"]
        assert time_str.endswith("s")
        assert float(time_str.rstrip("s")) >= 0
    
    def test_rate_limit_headers_present(self):
        """Test that rate limit headers are added"""
        response = client.get("/")
        
        assert response.status_code == 200
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
    
    def test_validation_error_format(self):
        """Test that validation errors return structured format"""
        response = client.post("/v1/chat", json={})  # Missing required 'message' field
        
        assert response.status_code == 422
        data = response.json()
        assert "error" in data
        assert data["error"] == "Validation error"
        assert "errors" in data
        assert isinstance(data["errors"], list)
        # Each error should have field, message, and type
        for error in data["errors"]:
            assert "field" in error
            assert "message" in error
            assert "type" in error


class TestCORSHeaders:
    """Test CORS configuration"""
    
    def test_cors_preflight(self):
        """Test CORS preflight requests"""
        response = client.options("/", headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type"
        })
        
        # FastAPI CORS middleware handles this
        assert response.status_code in [200, 405]  # 405 if not configured for OPTIONS
