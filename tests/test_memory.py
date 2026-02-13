import pytest
import json
import os
import tempfile
import shutil
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from masterclaw_core.memory import (
    MemoryStore, JSONBackend, ChromaBackend, 
    MemoryEntry, get_memory_store
)


class TestJSONBackend:
    """Test JSON file-based memory backend"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files"""
        temp_path = tempfile.mkdtemp()
        yield temp_path
        shutil.rmtree(temp_path)
        
    @pytest.fixture
    def backend(self, temp_dir):
        """Create a JSON backend with temp directory"""
        file_path = os.path.join(temp_dir, "memories.json")
        return JSONBackend(file_path)
    
    @pytest.mark.asyncio
    async def test_add_memory(self, backend):
        """Test adding a memory entry"""
        entry = MemoryEntry(content="Test memory")
        memory_id = await backend.add(entry)
        
        assert memory_id is not None
        assert len(memory_id) == 32  # MD5 hash length
        
    @pytest.mark.asyncio
    async def test_add_memory_with_id(self, backend):
        """Test adding memory with custom ID"""
        entry = MemoryEntry(id="custom-id", content="Test")
        memory_id = await backend.add(entry)
        
        assert memory_id == "custom-id"
        
    @pytest.mark.asyncio
    async def test_get_memory(self, backend):
        """Test retrieving a memory by ID"""
        entry = MemoryEntry(content="Retrievable memory")
        memory_id = await backend.add(entry)
        
        retrieved = await backend.get(memory_id)
        assert retrieved is not None
        assert retrieved.content == "Retrievable memory"
        assert retrieved.id == memory_id
        
    @pytest.mark.asyncio
    async def test_get_nonexistent_memory(self, backend):
        """Test getting a memory that doesn't exist"""
        result = await backend.get("nonexistent-id")
        assert result is None
        
    @pytest.mark.asyncio
    async def test_search_memory(self, backend):
        """Test searching memories"""
        # Add some memories
        await backend.add(MemoryEntry(content="Python programming tips"))
        await backend.add(MemoryEntry(content="JavaScript best practices"))
        await backend.add(MemoryEntry(content="Python machine learning"))
        
        # Search
        results = await backend.search("Python", top_k=5)
        
        assert len(results) == 2
        assert all("Python" in r.content for r in results)
        
    @pytest.mark.asyncio
    async def test_search_with_filter(self, backend):
        """Test searching with metadata filter"""
        await backend.add(MemoryEntry(
            content="Important note",
            metadata={"category": "work"}
        ))
        await backend.add(MemoryEntry(
            content="Casual note",
            metadata={"category": "personal"}
        ))
        
        results = await backend.search("note", filter_metadata={"category": "work"})
        
        assert len(results) == 1
        assert results[0].metadata["category"] == "work"
        
    @pytest.mark.asyncio
    async def test_search_limit(self, backend):
        """Test search respects top_k limit"""
        for i in range(10):
            await backend.add(MemoryEntry(content=f"Memory {i}"))
            
        results = await backend.search("Memory", top_k=3)
        assert len(results) == 3
        
    @pytest.mark.asyncio
    async def test_delete_memory(self, backend):
        """Test deleting a memory"""
        entry = MemoryEntry(content="To be deleted")
        memory_id = await backend.add(entry)
        
        # Verify it exists
        assert await backend.get(memory_id) is not None
        
        # Delete it
        success = await backend.delete(memory_id)
        assert success is True
        
        # Verify it's gone
        assert await backend.get(memory_id) is None
        
    @pytest.mark.asyncio
    async def test_delete_nonexistent_memory(self, backend):
        """Test deleting a memory that doesn't exist"""
        success = await backend.delete("nonexistent-id")
        assert success is False
        
    @pytest.mark.asyncio
    async def test_persistence(self, temp_dir):
        """Test that data persists to disk"""
        file_path = os.path.join(temp_dir, "memories.json")
        
        # Create backend and add memory
        backend1 = JSONBackend(file_path)
        entry = MemoryEntry(content="Persistent memory")
        memory_id = await backend1.add(entry)
        
        # Create new backend instance (simulates restart)
        backend2 = JSONBackend(file_path)
        retrieved = await backend2.get(memory_id)
        
        assert retrieved is not None
        assert retrieved.content == "Persistent memory"


class TestMemoryStore:
    """Test MemoryStore high-level interface"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory"""
        temp_path = tempfile.mkdtemp()
        yield temp_path
        shutil.rmtree(temp_path)
        
    @pytest.mark.asyncio
    async def test_add_memory_with_params(self, temp_dir):
        """Test adding memory with all parameters"""
        store = MemoryStore(backend="json")
        
        memory_id = await store.add(
            content="Test content",
            metadata={"session_id": "abc", "user": "test"},
            source="chat"
        )
        
        assert memory_id is not None
        
        # Verify it was stored
        entry = await store.get(memory_id)
        assert entry.content == "Test content"
        assert entry.metadata["session_id"] == "abc"
        assert entry.source == "chat"
        
    @pytest.mark.asyncio
    async def test_search_interface(self, temp_dir):
        """Test search through store interface"""
        store = MemoryStore(backend="json")
        
        await store.add("Python is great", metadata={"lang": "python"})
        await store.add("JavaScript is cool", metadata={"lang": "js"})
        
        results = await store.search("Python", top_k=3)
        assert len(results) >= 1
        
    @pytest.mark.asyncio
    async def test_invalid_backend(self):
        """Test that invalid backend raises error"""
        with pytest.raises(ValueError, match="Unknown backend"):
            MemoryStore(backend="invalid")


class TestGetMemoryStore:
    """Test get_memory_store singleton function"""
    
    def test_returns_singleton(self):
        """Test that get_memory_store returns the same instance"""
        from masterclaw_core.memory import memory_store
        
        # Reset the singleton for testing
        import masterclaw_core.memory
        masterclaw_core.memory.memory_store = None
        
        store1 = get_memory_store()
        store2 = get_memory_store()
        
        assert store1 is store2


class TestMemoryEntryTimestamps:
    """Test timestamp handling in memories"""
    
    @pytest.mark.asyncio
    async def test_timestamp_preserved(self):
        """Test that timestamps are preserved correctly"""
        store = MemoryStore(backend="json")
        
        custom_time = datetime(2024, 1, 15, 10, 30, 0)
        entry = MemoryEntry(content="Test", timestamp=custom_time)
        
        # Add and retrieve
        memory_id = await store.backend.add(entry)
        retrieved = await store.backend.get(memory_id)
        
        assert retrieved.timestamp.year == 2024
        assert retrieved.timestamp.month == 1
