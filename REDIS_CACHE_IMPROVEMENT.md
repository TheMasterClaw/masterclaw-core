# Redis Caching Layer Implementation Plan

## Overview
Add Redis as a distributed caching and session store to enable horizontal scaling and improve performance for production deployments.

## Why This Matters

1. **Horizontal Scaling**: Current rate limiting and session tracking are in-memory only. When running multiple Core pods in Kubernetes, each pod has its own isolated state.

2. **Session Persistence**: Sessions are currently stored in memory. A Redis backend would allow sessions to survive pod restarts.

3. **Performance**: Caching LLM responses, embeddings, and expensive operations reduces latency and API costs.

4. **Rate Limiting**: Distributed rate limiting across all Core instances.

## Implementation

### 1. Infrastructure - Docker Compose (✅ Done)
- Added `redis` service to docker-compose.yml
- Configured with persistence and health checks
- Connected to masterclaw-network
- Added to Core's depends_on

### 2. Infrastructure - Kubernetes (✅ Done)
- Added Redis StatefulSet with persistent storage
- Added Redis Service for internal communication
- Configured resource limits and security context

### 3. Core - Configuration (✅ Done)
- Added Redis settings to config.py
- Added validation for Redis connection parameters
- Added Redis URL construction

### 4. Core - Redis Client (✅ Done)
- Created cache.py with Redis client wrapper
- Implemented connection pooling and error handling
- Added key prefixing for namespace isolation
- Implemented serialization for complex objects

### 5. Core - Enhanced Rate Limiting (✅ Done)
- Updated middleware.py with Redis-backed rate limiting
- Falls back to memory if Redis unavailable
- Supports sliding window algorithm
- Added distributed rate limit sync

### 6. Core - Session Store (✅ Done)
- Created session_store.py with Redis backend
- Session persistence across restarts
- Configurable TTL
- Atomic operations for session updates

### 7. Core - LLM Response Caching (✅ Done)
- Cache LLM responses to reduce API costs
- Configurable TTL per provider
- Cache key based on model + message hash
- Skip cache for streaming requests

### 8. Core - Embedding Cache (✅ Done)
- Cache embeddings to avoid recomputation
- Significant performance improvement for repeated queries
- Configurable TTL

### 9. Core - API Endpoints (✅ Done)
- GET /cache/stats - View cache statistics
- POST /cache/clear - Clear cache (admin)
- GET /cache/health - Redis connection health

### 10. Tools - CLI Commands (✅ Done)
- mc cache stats - View cache statistics
- mc cache clear - Clear cache
- mc cache warm - Pre-populate cache

## Benefits

| Metric | Before | After |
|--------|--------|-------|
| Session persistence | Pod-local | Shared across pods |
| Rate limiting scope | Single pod | All pods |
| Embedding computation | Every request | Cached |
| LLM API calls | Every request | Cached (configurable) |
| Failover | None | Automatic fallback |

## Files Modified

### Infrastructure
- masterclaw-infrastructure/docker-compose.yml
- masterclaw-infrastructure/k8s/base/redis.yaml (new)
- masterclaw-infrastructure/k8s/base/kustomization.yaml

### Core
- masterclaw_core/config.py
- masterclaw_core/cache.py (new)
- masterclaw_core/session_store.py (new)
- masterclaw_core/middleware.py
- masterclaw_core/main.py
- masterclaw_core/llm.py

### Tools
- masterclaw-tools/lib/cache.js (new)
- masterclaw-tools/bin/mc.js

## Testing

```bash
# Start with Redis
cd masterclaw-infrastructure && make prod

# Check Redis health
curl http://localhost:8000/cache/health

# View cache stats
curl http://localhost:8000/cache/stats

# Or via CLI
mc cache stats
```

## Security Considerations

- Redis runs without external exposure (internal network only)
- No AUTH configured for internal cluster use (can be added)
- Cache keys are namespaced to prevent collisions
- Sensitive data (API keys, tokens) is never cached
