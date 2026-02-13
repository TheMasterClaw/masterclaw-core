"""Memory management for MasterClaw Core"""

import os
import json
import hashlib
from typing import List, Optional, Dict, Any
from datetime import datetime
from abc import ABC, abstractmethod

import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer

from .models import MemoryEntry
from .config import settings


class MemoryBackend(ABC):
    """Abstract base class for memory backends"""
    
    @abstractmethod
    async def add(self, entry: MemoryEntry) -> str:
        """Add a memory entry and return its ID"""
        pass
    
    @abstractmethod
    async def search(
        self,
        query: str,
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[MemoryEntry]:
        """Search for memories"""
        pass
    
    @abstractmethod
    async def get(self, memory_id: str) -> Optional[MemoryEntry]:
        """Get a specific memory by ID"""
        pass
    
    @abstractmethod
    async def delete(self, memory_id: str) -> bool:
        """Delete a memory by ID"""
        pass


class ChromaBackend(MemoryBackend):
    """ChromaDB vector database backend"""
    
    def __init__(self, persist_dir: str = "./data/chroma"):
        self.persist_dir = persist_dir
        os.makedirs(persist_dir, exist_ok=True)
        
        self.client = chromadb.Client(
            ChromaSettings(
                persist_directory=persist_dir,
                anonymized_telemetry=False,
            )
        )
        
        self.collection = self.client.get_or_create_collection(
            name="masterclaw_memories",
            metadata={"hnsw:space": "cosine"}
        )
        
        # Load embedding model
        self.embedder = SentenceTransformer(settings.EMBEDDING_MODEL)
    
    async def add(self, entry: MemoryEntry) -> str:
        """Add a memory entry"""
        memory_id = entry.id or hashlib.md5(
            f"{entry.content}{entry.timestamp}".encode()
        ).hexdigest()
        
        # Generate embedding
        embedding = self.embedder.encode(entry.content).tolist()
        
        # Store in Chroma
        self.collection.add(
            ids=[memory_id],
            embeddings=[embedding],
            documents=[entry.content],
            metadatas=[{
                **entry.metadata,
                "timestamp": entry.timestamp.isoformat(),
                "source": entry.source or "unknown",
            }]
        )
        
        return memory_id
    
    async def search(
        self,
        query: str,
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[MemoryEntry]:
        """Search memories using semantic similarity"""
        # Generate query embedding
        query_embedding = self.embedder.encode(query).tolist()
        
        # Search Chroma
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=filter_metadata,
        )
        
        memories = []
        if results["ids"] and results["ids"][0]:
            for i, memory_id in enumerate(results["ids"][0]):
                content = results["documents"][0][i]
                metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                
                memories.append(MemoryEntry(
                    id=memory_id,
                    content=content,
                    metadata={k: v for k, v in metadata.items() if k not in ["timestamp", "source"]},
                    timestamp=datetime.fromisoformat(metadata.get("timestamp", datetime.utcnow().isoformat())),
                    source=metadata.get("source"),
                ))
        
        return memories
    
    async def get(self, memory_id: str) -> Optional[MemoryEntry]:
        """Get a specific memory"""
        try:
            result = self.collection.get(ids=[memory_id])
            if result["ids"]:
                metadata = result["metadatas"][0] if result["metadatas"] else {}
                return MemoryEntry(
                    id=memory_id,
                    content=result["documents"][0],
                    metadata={k: v for k, v in metadata.items() if k not in ["timestamp", "source"]},
                    timestamp=datetime.fromisoformat(metadata.get("timestamp", datetime.utcnow().isoformat())),
                    source=metadata.get("source"),
                )
        except Exception:
            pass
        return None
    
    async def delete(self, memory_id: str) -> bool:
        """Delete a memory"""
        try:
            self.collection.delete(ids=[memory_id])
            return True
        except Exception:
            return False


class JSONBackend(MemoryBackend):
    """Simple JSON file backend for testing/small deployments"""
    
    def __init__(self, file_path: str = "./data/memories.json"):
        self.file_path = file_path
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        self._memories: Dict[str, Dict[str, Any]] = {}
        self._load()
    
    def _load(self):
        """Load memories from disk"""
        if os.path.exists(self.file_path):
            with open(self.file_path, "r") as f:
                self._memories = json.load(f)
    
    def _save(self):
        """Save memories to disk"""
        with open(self.file_path, "w") as f:
            json.dump(self._memories, f, indent=2, default=str)
    
    async def add(self, entry: MemoryEntry) -> str:
        """Add a memory entry"""
        memory_id = entry.id or hashlib.md5(
            f"{entry.content}{datetime.utcnow()}".encode()
        ).hexdigest()
        
        self._memories[memory_id] = {
            "content": entry.content,
            "metadata": entry.metadata,
            "timestamp": entry.timestamp.isoformat(),
            "source": entry.source,
        }
        self._save()
        return memory_id
    
    async def search(
        self,
        query: str,
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[MemoryEntry]:
        """Simple text search (no semantic similarity)"""
        results = []
        query_lower = query.lower()
        
        for memory_id, data in self._memories.items():
            # Simple text matching
            if query_lower in data["content"].lower():
                # Apply metadata filter
                if filter_metadata:
                    if not all(
                        data["metadata"].get(k) == v 
                        for k, v in filter_metadata.items()
                    ):
                        continue
                
                results.append(MemoryEntry(
                    id=memory_id,
                    content=data["content"],
                    metadata=data["metadata"],
                    timestamp=datetime.fromisoformat(data["timestamp"]),
                    source=data.get("source"),
                ))
        
        # Sort by timestamp (newest first) and limit
        results.sort(key=lambda x: x.timestamp, reverse=True)
        return results[:top_k]
    
    async def get(self, memory_id: str) -> Optional[MemoryEntry]:
        """Get a specific memory"""
        data = self._memories.get(memory_id)
        if data:
            return MemoryEntry(
                id=memory_id,
                content=data["content"],
                metadata=data["metadata"],
                timestamp=datetime.fromisoformat(data["timestamp"]),
                source=data.get("source"),
            )
        return None
    
    async def delete(self, memory_id: str) -> bool:
        """Delete a memory"""
        if memory_id in self._memories:
            del self._memories[memory_id]
            self._save()
            return True
        return False


class MemoryStore:
    """High-level memory store interface"""
    
    def __init__(self, backend: Optional[str] = None):
        backend = backend or settings.MEMORY_BACKEND
        
        if backend == "chroma":
            self.backend = ChromaBackend(settings.CHROMA_PERSIST_DIR)
        elif backend == "json":
            self.backend = JSONBackend("./data/memories.json")
        else:
            raise ValueError(f"Unknown backend: {backend}")
    
    async def add(self, content: str, metadata: Optional[Dict[str, Any]] = None, source: Optional[str] = None) -> str:
        """Add a memory"""
        entry = MemoryEntry(
            content=content,
            metadata=metadata or {},
            source=source,
        )
        return await self.backend.add(entry)
    
    async def search(self, query: str, top_k: int = 5, **kwargs) -> List[MemoryEntry]:
        """Search memories"""
        return await self.backend.search(query, top_k, **kwargs)
    
    async def get(self, memory_id: str) -> Optional[MemoryEntry]:
        """Get a memory"""
        return await self.backend.get(memory_id)
    
    async def delete(self, memory_id: str) -> bool:
        """Delete a memory"""
        return await self.backend.delete(memory_id)


# Global store instance
memory_store: Optional[MemoryStore] = None


def get_memory_store() -> MemoryStore:
    """Get or create global memory store"""
    global memory_store
    if memory_store is None:
        memory_store = MemoryStore()
    return memory_store
