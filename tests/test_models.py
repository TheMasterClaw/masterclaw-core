import pytest
from datetime import datetime
from masterclaw_core.models import (
    ChatRequest, ChatResponse, MemoryEntry, 
    MemorySearchRequest, MemorySearchResponse, HealthResponse
)


class TestChatRequest:
    """Test ChatRequest model validation"""
    
    def test_valid_chat_request(self):
        """Test creating a valid chat request"""
        request = ChatRequest(message="Hello")
        assert request.message == "Hello"
        assert request.temperature == 0.7
        assert request.use_memory is True
        
    def test_chat_request_temperature_bounds(self):
        """Test temperature must be between 0 and 2"""
        with pytest.raises(ValueError):
            ChatRequest(message="Hello", temperature=3.0)
        with pytest.raises(ValueError):
            ChatRequest(message="Hello", temperature=-0.1)
            
    def test_chat_request_empty_message(self):
        """Test message cannot be empty"""
        with pytest.raises(ValueError):
            ChatRequest(message="")
            
    def test_chat_request_max_tokens_bounds(self):
        """Test max_tokens validation"""
        with pytest.raises(ValueError):
            ChatRequest(message="Hello", max_tokens=5000)
        with pytest.raises(ValueError):
            ChatRequest(message="Hello", max_tokens=0)


class TestChatResponse:
    """Test ChatResponse model"""
    
    def test_valid_chat_response(self):
        """Test creating a valid chat response"""
        response = ChatResponse(
            response="Hello there!",
            model="gpt-4",
            provider="openai"
        )
        assert response.response == "Hello there!"
        assert response.model == "gpt-4"
        assert response.provider == "openai"
        assert response.memories_used == 0
        assert isinstance(response.timestamp, datetime)


class TestMemoryEntry:
    """Test MemoryEntry model"""
    
    def test_valid_memory_entry(self):
        """Test creating a valid memory entry"""
        entry = MemoryEntry(content="Test memory content")
        assert entry.content == "Test memory content"
        assert entry.metadata == {}
        assert isinstance(entry.timestamp, datetime)
        
    def test_memory_entry_empty_content(self):
        """Test content cannot be empty"""
        with pytest.raises(ValueError):
            MemoryEntry(content="")
            
    def test_memory_entry_with_metadata(self):
        """Test memory with metadata"""
        entry = MemoryEntry(
            content="Test",
            metadata={"session_id": "abc123", "type": "chat"},
            source="test_source"
        )
        assert entry.metadata["session_id"] == "abc123"
        assert entry.source == "test_source"


class TestMemorySearchRequest:
    """Test MemorySearchRequest model"""
    
    def test_valid_search_request(self):
        """Test creating a valid search request"""
        request = MemorySearchRequest(query="test")
        assert request.query == "test"
        assert request.top_k == 5
        
    def test_search_request_top_k_bounds(self):
        """Test top_k validation"""
        with pytest.raises(ValueError):
            MemorySearchRequest(query="test", top_k=0)
        with pytest.raises(ValueError):
            MemorySearchRequest(query="test", top_k=25)
            
    def test_search_request_empty_query(self):
        """Test query cannot be empty"""
        with pytest.raises(ValueError):
            MemorySearchRequest(query="")


class TestMemorySearchResponse:
    """Test MemorySearchResponse model"""
    
    def test_valid_search_response(self):
        """Test creating a valid search response"""
        response = MemorySearchResponse(query="test")
        assert response.query == "test"
        assert response.results == []
        assert response.total_results == 0


class TestHealthResponse:
    """Test HealthResponse model"""
    
    def test_valid_health_response(self):
        """Test creating a valid health response"""
        response = HealthResponse(
            version="1.0.0",
            services={"memory": "chroma"}
        )
        assert response.status == "healthy"
        assert response.version == "1.0.0"
        assert response.services["memory"] == "chroma"
        assert isinstance(response.timestamp, datetime)


class TestModelSerialization:
    """Test model serialization/deserialization"""
    
    def test_chat_request_json(self):
        """Test ChatRequest can be serialized to JSON"""
        request = ChatRequest(message="Hello", session_id="abc")
        json_data = request.model_dump()
        assert json_data["message"] == "Hello"
        assert json_data["session_id"] == "abc"
        
    def test_memory_entry_json(self):
        """Test MemoryEntry JSON serialization"""
        entry = MemoryEntry(content="Test", metadata={"key": "value"})
        json_data = entry.model_dump()
        assert json_data["content"] == "Test"
        assert json_data["metadata"]["key"] == "value"
