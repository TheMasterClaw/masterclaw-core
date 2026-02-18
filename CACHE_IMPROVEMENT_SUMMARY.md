# MasterClaw Ecosystem Improvement: API Response Caching (Feb 2026)

## Summary

Added **API Response Caching** to MasterClaw Core to reduce LLM API costs and improve response times. This feature caches GET request responses and intelligently invalidates them on write operations.

## What Was Improved

### 1. New Module: `masterclaw_core/cache.py`

A comprehensive caching system with:

- **MemoryCache class** - In-memory cache with TTL support
- **CacheMiddleware** - FastAPI middleware for automatic request/response caching
- **CacheEntry & CacheStats** - Data classes for cache entries and statistics
- **Cached decorator** - Function-level caching for expensive operations
- **Global cache instance** - Shared cache across the application

### 2. Cache Features

| Feature | Description |
|---------|-------------|
| **Automatic GET caching** | Identical GET requests served from cache |
| **Smart invalidation** | POST/PUT/DELETE auto-invalidate related caches |
| **Per-endpoint TTL** | Different cache durations for different endpoints |
| **Cache headers** | `X-Cache: HIT/MISS` and age/TTL headers |
| **Skip cache** | Bypass with `Cache-Control: no-cache` header |
| **Statistics** | Hit rate, memory usage, entry count |

### 3. Cache TTL Configuration

| Endpoint Pattern | TTL | Reason |
|-----------------|-----|--------|
| `/v1/memory/search` | 60s | Frequent searches need fresh results |
| `/v1/sessions` | 30s | Session lists change often |
| `/v1/sessions/{id}` | 60s | Individual sessions |
| `/v1/costs` | 300s | Cost data relatively stable |
| `/v1/analytics/*` | 60s | Analytics updates frequently |
| Default | 60s | Safe default for other endpoints |

### 4. New API Endpoints

```bash
# View cache statistics
GET /cache/stats

# Clear all cached responses  
POST /cache/clear

# List cached keys (debugging)
GET /cache/keys?pattern=memory&limit=100
```

### 5. Configuration Options

```bash
# .env configuration
CACHE_ENABLED=true              # Enable/disable caching
CACHE_BACKEND=memory            # 'memory' or 'redis'
CACHE_DEFAULT_TTL=300           # Default TTL in seconds
CACHE_MAX_SIZE=1000             # Max entries (memory backend)
CACHE_REDIS_URL=redis://...     # Redis URL (if using Redis)
```

### 6. Updated Configuration Validation

Added validators for cache settings:
- `CACHE_BACKEND`: Must be 'memory' or 'redis'
- `CACHE_DEFAULT_TTL`: 0-86400 seconds (24 hours max)
- `CACHE_MAX_SIZE`: 100-100000 entries

## Files Changed

| Repository | File | Change |
|------------|------|--------|
| masterclaw-core | `masterclaw_core/cache.py` | **New module** - Caching system (365 lines) |
| masterclaw-core | `masterclaw_core/config.py` | Added cache configuration options |
| masterclaw-core | `masterclaw_core/main.py` | Integrated cache middleware + endpoints |
| masterclaw-core | `.env.example` | Added cache configuration section |
| masterclaw-core | `README.md` | Added caching documentation |
| masterclaw-core | `tests/test_cache.py` | **New test file** - 29 comprehensive tests |

## Test Results

```
============================= test session starts ==============================
platform linux -- Python 3.12.3

tests/test_cache.py::TestCacheEntry::test_cache_entry_creation PASSED
tests/test_cache.py::TestCacheEntry::test_cache_entry_expired PASSED
...
tests/test_cache.py::TestGlobalCache::test_get_cache_stats PASSED

============================== 29 passed ===============================
```

## Benefits

1. **💰 Reduced LLM Costs** - Repeated identical queries hit cache instead of calling LLM APIs
2. **⚡ Faster Response Times** - Cached responses served in <1ms vs 100-500ms for LLM calls
3. **🔄 Less API Load** - Reduces pressure on external LLM providers
4. **📊 Observability** - Monitor cache hit rates via `/cache/stats`
5. **🔧 Configurable** - Easy to tune TTL and disable per-environment

## Example Usage

```bash
# First request - cache miss
curl http://localhost:8000/v1/memory/search?q=backup
# Response header: X-Cache: MISS

# Second request - cache hit (within TTL)
curl http://localhost:8000/v1/memory/search?q=backup  
# Response header: X-Cache: HIT

# View statistics
curl http://localhost:8000/cache/stats
# {"hits": 45, "misses": 12, "hit_rate": 78.95, ...}

# Clear cache
curl -X POST http://localhost:8000/cache/clear
```

## Cache Invalidation

The cache automatically invalidates related entries on write operations:

| Write Operation | Invalidates |
|-----------------|-------------|
| `POST /v1/memory/*` | All `/v1/memory/*` cache entries |
| `DELETE /v1/sessions/{id}` | All `/v1/sessions/*` cache entries |
| `POST /v1/costs/*` | All `/v1/costs/*` cache entries |

This ensures data consistency without manual cache management.

## Version

masterclaw-core with API Response Caching
