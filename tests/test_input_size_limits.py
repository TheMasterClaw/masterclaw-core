"""Tests for input size validation and DoS prevention

These tests verify that the API properly rejects oversized inputs
to prevent DoS attacks and resource exhaustion.
"""

import pytest
from pydantic import ValidationError

from masterclaw_core.models import (
    ChatRequest,
    MemoryEntry,
    MemorySearchRequest,
)


class TestChatRequestSizeLimits:
    """Test size limits for chat requests"""
    
    def test_message_max_length_accepted(self):
        """Test that message at max length is accepted"""
        # Max is 100000, so 100000 chars should work
        request = ChatRequest(message="x" * 100000)
        assert len(request.message) == 100000
    
    def test_message_exceeds_max_length_rejected(self):
        """Test that message exceeding max length is rejected"""
        with pytest.raises(ValidationError) as exc_info:
            ChatRequest(message="x" * 100001)
        
        assert "message" in str(exc_info.value)
        assert "100000" in str(exc_info.value)
    
    def test_session_id_max_length_accepted(self):
        """Test that session_id at max length (64) is accepted"""
        request = ChatRequest(
            message="Hello",
            session_id="x" * 64
        )
        assert len(request.session_id) == 64
    
    def test_session_id_exceeds_max_length_rejected(self):
        """Test that session_id exceeding 64 chars is rejected"""
        with pytest.raises(ValidationError) as exc_info:
            ChatRequest(
                message="Hello",
                session_id="x" * 65
            )
        
        assert "session_id" in str(exc_info.value)
    
    def test_model_name_max_length_accepted(self):
        """Test that model name at max length (100) is accepted"""
        request = ChatRequest(
            message="Hello",
            model="x" * 100
        )
        assert len(request.model) == 100
    
    def test_model_name_exceeds_max_length_rejected(self):
        """Test that model name exceeding 100 chars is rejected"""
        with pytest.raises(ValidationError) as exc_info:
            ChatRequest(
                message="Hello",
                model="x" * 101
            )
        
        assert "model" in str(exc_info.value)
    
    def test_system_prompt_max_length_accepted(self):
        """Test that system_prompt at max length (10000) is accepted"""
        request = ChatRequest(
            message="Hello",
            system_prompt="x" * 10000
        )
        assert len(request.system_prompt) == 10000
    
    def test_system_prompt_exceeds_max_length_rejected(self):
        """Test that system_prompt exceeding 10000 chars is rejected"""
        with pytest.raises(ValidationError) as exc_info:
            ChatRequest(
                message="Hello",
                system_prompt="x" * 10001
            )
        
        assert "system_prompt" in str(exc_info.value)


class TestMemoryEntrySizeLimits:
    """Test size limits for memory entries"""
    
    def test_content_max_length_accepted(self):
        """Test that content at max length (500000) is accepted"""
        entry = MemoryEntry(content="x" * 500000)
        assert len(entry.content) == 500000
    
    def test_content_exceeds_max_length_rejected(self):
        """Test that content exceeding max length is rejected"""
        with pytest.raises(ValidationError) as exc_info:
            MemoryEntry(content="x" * 500001)
        
        assert "content" in str(exc_info.value)
        assert "500000" in str(exc_info.value)
    
    def test_memory_id_max_length_accepted(self):
        """Test that memory ID at max length (64) is accepted"""
        entry = MemoryEntry(
            id="x" * 64,
            content="Test content"
        )
        assert len(entry.id) == 64
    
    def test_memory_id_exceeds_max_length_rejected(self):
        """Test that memory ID exceeding 64 chars is rejected"""
        with pytest.raises(ValidationError) as exc_info:
            MemoryEntry(
                id="x" * 65,
                content="Test content"
            )
        
        assert "id" in str(exc_info.value)
    
    def test_source_max_length_accepted(self):
        """Test that source at max length (256) is accepted"""
        entry = MemoryEntry(
            content="Test content",
            source="x" * 256
        )
        assert len(entry.source) == 256
    
    def test_source_exceeds_max_length_rejected(self):
        """Test that source exceeding 256 chars is rejected"""
        with pytest.raises(ValidationError) as exc_info:
            MemoryEntry(
                content="Test content",
                source="x" * 257
            )
        
        assert "source" in str(exc_info.value)


class TestMemorySearchRequestSizeLimits:
    """Test size limits for memory search requests"""
    
    def test_query_max_length_accepted(self):
        """Test that query at max length (10000) is accepted"""
        request = MemorySearchRequest(query="x" * 10000)
        assert len(request.query) == 10000
    
    def test_query_exceeds_max_length_rejected(self):
        """Test that query exceeding max length is rejected"""
        with pytest.raises(ValidationError) as exc_info:
            MemorySearchRequest(query="x" * 10001)
        
        assert "query" in str(exc_info.value)
        assert "10000" in str(exc_info.value)


class TestDoSPreventionScenarios:
    """Security-focused tests for DoS prevention via oversized inputs"""
    
    def test_giant_message_rejected(self):
        """Test that extremely large messages (10MB+) are rejected"""
        giant_message = "A" * (10 * 1024 * 1024)  # 10MB
        
        with pytest.raises(ValidationError) as exc_info:
            ChatRequest(message=giant_message)
        
        # Should be rejected quickly without processing
        assert "message" in str(exc_info.value)
    
    def test_giant_memory_content_rejected(self):
        """Test that extremely large memory content is rejected"""
        giant_content = "B" * (5 * 1024 * 1024)  # 5MB
        
        with pytest.raises(ValidationError) as exc_info:
            MemoryEntry(content=giant_content)
        
        assert "content" in str(exc_info.value)
    
    def test_nested_large_metadata_still_validates_content(self):
        """Test that even with complex metadata, content size is enforced"""
        large_metadata = {"nested": {"deep": {"data": "x" * 1000}}}
        
        # This should fail due to content size, not metadata
        with pytest.raises(ValidationError) as exc_info:
            MemoryEntry(
                content="y" * 500001,  # Exceeds limit
                metadata=large_metadata
            )
        
        assert "content" in str(exc_info.value)
    
    def test_empty_message_still_rejected(self):
        """Test that empty messages are still rejected (min_length check)"""
        with pytest.raises(ValidationError) as exc_info:
            ChatRequest(message="")
        
        assert "message" in str(exc_info.value)
    
    def test_whitespace_only_message_accepted(self):
        """Test that whitespace-only messages are accepted (they have length > 0)"""
        # Whitespace has length > 0, so it should be accepted
        request = ChatRequest(message="   ")
        assert len(request.message) == 3  # Three spaces


class TestBoundaryValues:
    """Test boundary values for size limits"""
    
    @pytest.mark.parametrize("size,should_pass", [
        (1, True),       # Minimum valid
        (100, True),     # Small valid
        (99999, True),   # Just under max
        (100000, True),  # Exactly at max
        (100001, False), # Just over max
    ])
    def test_chat_message_boundaries(self, size, should_pass):
        """Test message size boundaries"""
        if should_pass:
            request = ChatRequest(message="x" * size)
            assert len(request.message) == size
        else:
            with pytest.raises(ValidationError):
                ChatRequest(message="x" * size)
    
    @pytest.mark.parametrize("size,should_pass", [
        (1, True),
        (499999, True),
        (500000, True),
        (500001, False),
    ])
    def test_memory_content_boundaries(self, size, should_pass):
        """Test memory content size boundaries"""
        if should_pass:
            entry = MemoryEntry(content="x" * size)
            assert len(entry.content) == size
        else:
            with pytest.raises(ValidationError):
                MemoryEntry(content="x" * size)
    
    @pytest.mark.parametrize("size,should_pass", [
        (1, True),
        (9999, True),
        (10000, True),
        (10001, False),
    ])
    def test_search_query_boundaries(self, size, should_pass):
        """Test search query size boundaries"""
        if should_pass:
            request = MemorySearchRequest(query="x" * size)
            assert len(request.query) == size
        else:
            with pytest.raises(ValidationError):
                MemorySearchRequest(query="x" * size)
