"""Memory management for MasterClaw Core"""

import os
import json
import hashlib
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from abc import ABC, abstractmethod

import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer

from .models import MemoryEntry
from .config import settings
from .exceptions import MemoryNotFoundException

logger = logging.getLogger("masterclaw.memory")


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
        
        try:
            os.makedirs(persist_dir, exist_ok=True)
        except OSError as e:
            logger.error(f"Failed to create ChromaDB directory {persist_dir}: {e}")
            raise RuntimeError(f"Cannot initialize ChromaDB backend: {e}") from e
        
        try:
            self.client = chromadb.Client(
                ChromaSettings(
                    persist_directory=persist_dir,
                    anonymized_telemetry=False,
                )
            )
            logger.debug(f"ChromaDB client initialized with persist_dir: {persist_dir}")
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB client: {e}")
            raise RuntimeError(f"Cannot initialize ChromaDB client: {e}") from e
        
        try:
            self.collection = self.client.get_or_create_collection(
                name="masterclaw_memories",
                metadata={"hnsw:space": "cosine"}
            )
            logger.info(f"ChromaDB collection 'masterclaw_memories' ready")
        except chromadb.errors.ChromaError as e:
            logger.error(f"Failed to create/access ChromaDB collection: {e}")
            raise RuntimeError(f"Cannot initialize ChromaDB collection: {e}") from e
        
        # Load embedding model
        try:
            self.embedder = SentenceTransformer(settings.EMBEDDING_MODEL)
            logger.info(f"Embedding model '{settings.EMBEDDING_MODEL}' loaded")
        except Exception as e:
            logger.error(f"Failed to load embedding model '{settings.EMBEDDING_MODEL}': {e}")
            raise RuntimeError(f"Cannot load embedding model: {e}") from e
    
    async def add(self, entry: MemoryEntry) -> str:
        """Add a memory entry with error handling"""
        try:
            memory_id = entry.id or hashlib.md5(
                f"{entry.content}{entry.timestamp}".encode()
            ).hexdigest()
            
            # Generate embedding
            try:
                embedding = self.embedder.encode(entry.content).tolist()
            except Exception as e:
                logger.error(f"Failed to generate embedding for memory: {e}")
                raise RuntimeError(f"Embedding generation failed: {e}") from e
            
            # Store in Chroma
            try:
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
                logger.debug(f"Added memory with ID: {memory_id}")
            except chromadb.errors.ChromaError as e:
                logger.error(f"ChromaDB error adding memory: {e}")
                raise RuntimeError(f"Failed to store memory: {e}") from e
            
            return memory_id
            
        except RuntimeError:
            raise
        except Exception as e:
            logger.exception(f"Unexpected error adding memory")
            raise RuntimeError(f"Failed to add memory: {e}") from e
    
    async def search(
        self,
        query: str,
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[MemoryEntry]:
        """Search memories using semantic similarity with error handling"""
        try:
            # Generate query embedding
            try:
                query_embedding = self.embedder.encode(query).tolist()
            except Exception as e:
                logger.error(f"Failed to generate embedding for query '{query[:50]}...': {e}")
                return []
            
            # Search Chroma
            try:
                results = self.collection.query(
                    query_embeddings=[query_embedding],
                    n_results=top_k,
                    where=filter_metadata,
                )
            except chromadb.errors.ChromaError as e:
                logger.error(f"ChromaDB error during search: {e}")
                return []
            
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
            
            logger.debug(f"Search returned {len(memories)} results for query: {query[:50]}...")
            return memories
            
        except Exception as e:
            logger.exception(f"Unexpected error during memory search")
            return []
    
    async def get(self, memory_id: str) -> Optional[MemoryEntry]:
        """Get a specific memory by ID"""
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
        except chromadb.errors.IDNotFoundError:
            logger.debug(f"Memory ID not found: {memory_id}")
            return None
        except chromadb.errors.ChromaError as e:
            logger.error(f"ChromaDB error retrieving memory {memory_id}: {e}")
            return None
        except Exception as e:
            logger.exception(f"Unexpected error retrieving memory {memory_id}")
            return None
        
        return None
    
    async def delete(self, memory_id: str) -> bool:
        """Delete a memory by ID"""
        try:
            self.collection.delete(ids=[memory_id])
            logger.debug(f"Deleted memory: {memory_id}")
            return True
        except chromadb.errors.IDNotFoundError:
            logger.debug(f"Cannot delete - memory ID not found: {memory_id}")
            return False
        except chromadb.errors.ChromaError as e:
            logger.error(f"ChromaDB error deleting memory {memory_id}: {e}")
            return False
        except Exception as e:
            logger.exception(f"Unexpected error deleting memory {memory_id}")
            return False


class JSONBackend(MemoryBackend):
    """Simple JSON file backend for testing/small deployments"""
    
    def __init__(self, file_path: str = "./data/memories.json"):
        self.file_path = file_path
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        self._memories: Dict[str, Dict[str, Any]] = {}
        self._load()
    
    def _load(self):
        """Load memories from disk with error handling for corrupted files"""
        if not os.path.exists(self.file_path):
            logger.info(f"Memory file not found at {self.file_path}, starting with empty store")
            self._memories = {}
            return
        
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                self._memories = json.load(f)
            logger.debug(f"Loaded {len(self._memories)} memories from {self.file_path}")
        except json.JSONDecodeError as e:
            logger.error(f"Corrupted memory file at {self.file_path}: {e}. Starting with empty store.")
            self._memories = {}
            # Backup corrupted file
            backup_path = f"{self.file_path}.corrupted.{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
            try:
                os.rename(self.file_path, backup_path)
                logger.info(f"Backed up corrupted file to {backup_path}")
            except OSError as backup_err:
                logger.error(f"Failed to backup corrupted file: {backup_err}")
        except PermissionError as e:
            logger.error(f"Permission denied reading memory file {self.file_path}: {e}")
            self._memories = {}
        except Exception as e:
            logger.exception(f"Unexpected error loading memory file {self.file_path}")
            self._memories = {}
    
    def _save(self):
        """Save memories to disk with error handling"""
        try:
            # Write to temp file first, then rename for atomicity
            temp_path = f"{self.file_path}.tmp"
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(self._memories, f, indent=2, default=str)
            os.replace(temp_path, self.file_path)
            logger.debug(f"Saved {len(self._memories)} memories to {self.file_path}")
        except PermissionError as e:
            logger.error(f"Permission denied saving memory file {self.file_path}: {e}")
            raise MemoryError(f"Cannot save memories: permission denied") from e
        except OSError as e:
            logger.error(f"OS error saving memory file {self.file_path}: {e}")
            raise MemoryError(f"Cannot save memories: {e}") from e
        except Exception as e:
            logger.exception(f"Unexpected error saving memory file {self.file_path}")
            raise MemoryError(f"Cannot save memories: {e}") from e
    
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
