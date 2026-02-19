"""Redis caching layer for MasterClaw Core

Provides distributed caching for:
- LLM responses (reduce API costs)
- Embeddings (avoid recomputation)
- Session data (persistence across restarts)
- Rate limiting data (distributed rate limiting)
"""

import json
import hashlib
import logging
import pickle
from typing import Any, Optional, Dict, List
from datetime import timedelta

try:
    import redis
    from redis.exceptions import RedisError, ConnectionError
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from .config import settings

logger = logging.getLogger("masterclaw.cache")


class CacheClient:
    """Redis-based cache client with fallback to memory"""
    
    def __init__(self):
        self._redis: Optional[redis.Redis] = None
        self._memory_cache: Dict[str, tuple[Any, Optional[float]]] = {}
        self._enabled = settings.REDIS_ENABLED
        self._key_prefix = settings.REDIS_KEY_PREFIX
        
        if self._enabled and REDIS_AVAILABLE:
            try:
                self._redis = redis.from_url(
                    settings.REDIS_URL,
                    decode_responses=False,  # We handle serialization manually
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    health_check_interval=30,
                )
                # Test connection
                self._redis.ping()
                logger.info("Redis cache connected", url=settings.REDIS_URL)
            except (RedisError, ConnectionError) as e:
                logger.warning(
                    "Redis connection failed, falling back to memory cache",
                    error=str(e),
                    url=settings.REDIS_URL
                )
                self._redis = None
        elif not REDIS_AVAILABLE:
            logger.warning("Redis package not installed, using memory cache")
    
    def _make_key(self, key: str) -> str:
        """Create a prefixed key"""
        return f"{self._key_prefix}:{key}"
    
    def _serialize(self, value: Any) -> bytes:
        """Serialize a value to bytes"""
        return pickle.dumps(value)
    
    def _deserialize(self, data: bytes) -> Any:
        """Deserialize bytes to a value"""
        return pickle.loads(data)
    
    def get(self, key: str) -> Optional[Any]:
        """Get a value from cache"""
        if not self._enabled:
            return None
        
        full_key = self._make_key(key)
        
        # Try Redis first
        if self._redis:
            try:
                data = self._redis.get(full_key)
                if data:
                    return self._deserialize(data)
            except (RedisError, ConnectionError) as e:
                logger.debug("Redis get failed, trying memory", error=str(e))
        
        # Fallback to memory cache
        if key in self._memory_cache:
            value, expiry = self._memory_cache[key]
            if expiry is None or expiry > __import__('time').time():
                return value
            else:
                del self._memory_cache[key]
        
        return None
    
    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """Set a value in cache with optional TTL (seconds)"""
        if not self._enabled:
            return False
        
        full_key = self._make_key(key)
        ttl = ttl or settings.CACHE_TTL
        
        # Try Redis first
        if self._redis:
            try:
                data = self._serialize(value)
                self._redis.setex(full_key, ttl, data)
                return True
            except (RedisError, ConnectionError) as e:
                logger.debug("Redis set failed, using memory", error=str(e))
        
        # Fallback to memory cache
        import time
        expiry = time.time() + ttl if ttl else None
        self._memory_cache[key] = (value, expiry)
        return True
    
    def delete(self, key: str) -> bool:
        """Delete a key from cache"""
        if not self._enabled:
            return False
        
        full_key = self._make_key(key)
        
        # Try Redis first
        if self._redis:
            try:
                self._redis.delete(full_key)
                return True
            except (RedisError, ConnectionError) as e:
                logger.debug("Redis delete failed", error=str(e))
        
        # Fallback to memory cache
        if key in self._memory_cache:
            del self._memory_cache[key]
            return True
        
        return False
    
    def clear(self, pattern: Optional[str] = None) -> int:
        """Clear cache keys matching pattern (or all if no pattern)"""
        if not self._enabled:
            return 0
        
        count = 0
        
        # Try Redis first
        if self._redis:
            try:
                if pattern:
                    full_pattern = self._make_key(pattern)
                    keys = self._redis.keys(full_pattern)
                    if keys:
                        count = self._redis.delete(*keys)
                else:
                    # Get all keys with our prefix
                    keys = self._redis.keys(f"{self._key_prefix}:*")
                    if keys:
                        count = self._redis.delete(*keys)
                return count
            except (RedisError, ConnectionError) as e:
                logger.debug("Redis clear failed, using memory", error=str(e))
        
        # Fallback to memory cache
        if pattern:
            pattern_clean = pattern.replace("*", "")
            keys_to_delete = [
                k for k in self._memory_cache.keys()
                if pattern_clean in k
            ]
            for k in keys_to_delete:
                del self._memory_cache[k]
            count = len(keys_to_delete)
        else:
            count = len(self._memory_cache)
            self._memory_cache.clear()
        
        return count
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        stats = {
            "enabled": self._enabled,
            "redis_connected": self._redis is not None,
            "key_prefix": self._key_prefix,
            "memory_keys": len(self._memory_cache),
        }
        
        if self._redis:
            try:
                info = self._redis.info()
                stats["redis_version"] = info.get("redis_version")
                stats["used_memory_human"] = info.get("used_memory_human")
                stats["total_keys"] = self._redis.dbsize()
                stats["hit_rate"] = info.get("keyspace_hits", 0) / max(
                    info.get("keyspace_hits", 0) + info.get("keyspace_misses", 1), 1
                )
            except (RedisError, ConnectionError) as e:
                stats["redis_error"] = str(e)
        
        return stats
    
    def health_check(self) -> Dict[str, Any]:
        """Check cache health"""
        health = {
            "status": "healthy",
            "enabled": self._enabled,
            "backend": "unknown",
        }
        
        if not self._enabled:
            health["status"] = "disabled"
            return health
        
        if self._redis:
            try:
                self._redis.ping()
                health["backend"] = "redis"
                health["latency_ms"] = self._measure_latency()
            except (RedisError, ConnectionError) as e:
                health["status"] = "degraded"
                health["backend"] = "memory"
                health["redis_error"] = str(e)
        else:
            health["backend"] = "memory"
        
        return health
    
    def _measure_latency(self) -> float:
        """Measure Redis latency in milliseconds"""
        import time
        if not self._redis:
            return -1
        
        start = time.time()
        try:
            self._redis.ping()
        except:
            return -1
        end = time.time()
        
        return round((end - start) * 1000, 2)
    
    def increment(self, key: str, amount: int = 1, ttl: Optional[int] = None) -> int:
        """Atomically increment a counter"""
        if not self._enabled:
            # Return in-memory counter
            current = self._memory_cache.get(key, (0, None))[0]
            new_val = current + amount
            self._memory_cache[key] = (new_val, None)
            return new_val
        
        full_key = self._make_key(key)
        ttl = ttl or settings.CACHE_TTL
        
        # Try Redis first
        if self._redis:
            try:
                new_val = self._redis.incrby(full_key, amount)
                self._redis.expire(full_key, ttl)
                return new_val
            except (RedisError, ConnectionError):
                pass
        
        # Fallback
        current = self._memory_cache.get(key, (0, None))[0]
        new_val = current + amount
        import time
        self._memory_cache[key] = (new_val, time.time() + ttl)
        return new_val
    
    def expire(self, key: str, ttl: int) -> bool:
        """Set expiration on a key"""
        if not self._enabled:
            return False
        
        full_key = self._make_key(key)
        
        if self._redis:
            try:
                return self._redis.expire(full_key, ttl)
            except (RedisError, ConnectionError):
                pass
        
        # Memory fallback
        if key in self._memory_cache:
            value, _ = self._memory_cache[key]
            import time
            self._memory_cache[key] = (value, time.time() + ttl)
            return True
        
        return False


# Global cache instance
cache = CacheClient()


def get_cache() -> CacheClient:
    """Get the global cache instance"""
    return cache


def generate_cache_key(*parts: str) -> str:
    """Generate a cache key from parts"""
    combined = ":".join(parts)
    return hashlib.sha256(combined.encode()).hexdigest()[:32]


async def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics (async wrapper for cache.stats())"""
    return cache.stats()


async def clear_cache() -> bool:
    """Clear all cached data (async wrapper for cache.clear())"""
    return cache.clear()


class LLMCache:
    """Cache for LLM responses"""
    
    PREFIX = "llm"
    
    @classmethod
    def get_key(cls, provider: str, model: str, message: str, **kwargs) -> str:
        """Generate cache key for LLM request"""
        # Include relevant parameters in cache key
        key_parts = [provider, model, message]
        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}={v}")
        return f"{cls.PREFIX}:{generate_cache_key(*key_parts)}"
    
    @classmethod
    def get(cls, provider: str, model: str, message: str, **kwargs) -> Optional[Dict]:
        """Get cached LLM response"""
        if not settings.LLM_CACHE_ENABLED:
            return None
        
        key = cls.get_key(provider, model, message, **kwargs)
        return cache.get(key)
    
    @classmethod
    def set(
        cls,
        provider: str,
        model: str,
        message: str,
        response: Dict,
        **kwargs
    ) -> bool:
        """Cache LLM response"""
        if not settings.LLM_CACHE_ENABLED:
            return False
        
        key = cls.get_key(provider, model, message, **kwargs)
        return cache.set(key, response, settings.LLM_CACHE_TTL)


class EmbeddingCache:
    """Cache for embeddings"""
    
    PREFIX = "emb"
    
    @classmethod
    def get_key(cls, text: str, model: str) -> str:
        """Generate cache key for embedding"""
        return f"{cls.PREFIX}:{model}:{generate_cache_key(text)}"
    
    @classmethod
    def get(cls, text: str, model: str) -> Optional[List[float]]:
        """Get cached embedding"""
        if not settings.EMBEDDING_CACHE_ENABLED:
            return None
        
        key = cls.get_key(text, model)
        return cache.get(key)
    
    @classmethod
    def set(cls, text: str, model: str, embedding: List[float]) -> bool:
        """Cache embedding"""
        if not settings.EMBEDDING_CACHE_ENABLED:
            return False
        
        key = cls.get_key(text, model)
        return cache.set(key, embedding, settings.EMBEDDING_CACHE_TTL)


class RateLimitCache:
    """Distributed rate limiting using cache"""
    
    PREFIX = "ratelimit"
    
    @classmethod
    def get_key(cls, identifier: str, window: str) -> str:
        """Generate rate limit key"""
        return f"{cls.PREFIX}:{identifier}:{window}"
    
    @classmethod
    def increment(cls, identifier: str, window: str, ttl: int) -> int:
        """Increment counter for rate limit window"""
        key = cls.get_key(identifier, window)
        return cache.increment(key, 1, ttl)
    
    @classmethod
    def get(cls, identifier: str, window: str) -> int:
        """Get current count for rate limit window"""
        key = cls.get_key(identifier, window)
        value = cache.get(key)
        return value or 0
    
    @classmethod
    def reset(cls, identifier: str, window: Optional[str] = None) -> int:
        """Reset rate limit counters"""
        if window:
            key = cls.get_key(identifier, window)
            return 1 if cache.delete(key) else 0
        else:
            # Clear all windows for identifier
            pattern = f"{cls.PREFIX}:{identifier}:*"
            return cache.clear(pattern)
