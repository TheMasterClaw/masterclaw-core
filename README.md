# MasterClaw Core 🧠

The AI brain — LLM integrations, memory systems, agent orchestration, and tool handlers.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your API keys

# Run
python -m masterclaw_core
```

## API Endpoints

### Health
```bash
GET /health
```

### Security Health Check
```bash
GET /health/security
```

Returns security configuration status:
- `status`: "secure" or "insecure"
- `environment`: Current environment (development/production)
- `issues_count`: Number of security issues detected
- `recommendations_count`: Number of configuration recommendations

### Metrics (Prometheus)
```bash
GET /metrics
```

Returns Prometheus-formatted metrics for monitoring:
- `masterclaw_http_requests_total` - Total HTTP requests by method, endpoint, status
- `masterclaw_http_request_duration_seconds` - Request latency histogram
- `masterclaw_chat_requests_total` - Chat requests by provider and model
- `masterclaw_chat_tokens_total` - Token usage counter
- `masterclaw_memory_operations_total` - Memory operations by type and status
- `masterclaw_memory_search_duration_seconds` - Memory search latency
- `masterclaw_active_sessions` - Gauge of active sessions
- `masterclaw_memory_entries_total` - Gauge of total memory entries
- `masterclaw_llm_requests_total` - LLM API requests by provider
- `masterclaw_llm_request_duration_seconds` - LLM request latency

### Chat
```bash
POST /v1/chat
{
  "message": "Hello, MasterClaw!",
  "session_id": "abc123",
  "provider": "openai",
  "model": "gpt-4",
  "use_memory": true
}
```

### Memory
```bash
# Search memories
POST /v1/memory/search
{
  "query": "backup strategy",
  "top_k": 5
}

# Add memory
POST /v1/memory/add
{
  "content": "Remember to backup daily",
  "metadata": {"priority": "high"},
  "source": "user_instruction"
}

# Get memory
GET /v1/memory/{memory_id}

# Delete memory
DELETE /v1/memory/{memory_id}
```

### Sessions
```bash
# List all sessions
GET /v1/sessions?limit=100&active_since_hours=24

# Get session chat history
GET /v1/sessions/{session_id}?limit=50

# Delete a session and all its messages
DELETE /v1/sessions/{session_id}

# Get session statistics
GET /v1/sessions/stats/summary
```

## Architecture

```
masterclaw_core/
├── __init__.py        # Package info
├── __main__.py        # Entry point
├── main.py            # FastAPI app
├── config.py          # Settings with validation
├── models.py          # Pydantic models
├── llm.py             # LLM router (OpenAI, Anthropic)
└── memory.py          # Memory store (Chroma, JSON)
```

## Configuration

Configuration is validated on startup with security checks:

| Variable | Default | Description | Validation |
|----------|---------|-------------|------------|
| `OPENAI_API_KEY` | - | OpenAI API key | - |
| `ANTHROPIC_API_KEY` | - | Anthropic API key | - |
| `DEFAULT_MODEL` | gpt-4 | Default LLM model | - |
| `MEMORY_BACKEND` | chroma | Memory backend | Must be: chroma, json |
| `CHROMA_PERSIST_DIR` | ./data/chroma | ChromaDB directory | - |
| `PORT` | 8000 | API port | 1-65535 |
| `RATE_LIMIT_PER_MINUTE` | 60 | Rate limit per IP | 1-10000 |
| `CORS_ORIGINS` | ["*"] | Allowed CORS origins | Valid URLs; warns if "*" in production |
| `SESSION_TIMEOUT` | 3600 | Session timeout (seconds) | 60-604800 (7 days) |
| `LOG_LEVEL` | info | Logging level | debug, info, warning, error, critical |

### Security Validation

The configuration system includes security validators:

- **PORT**: Must be a valid port number (1-65535)
- **RATE_LIMIT_PER_MINUTE**: Must be reasonable (1-10000)
- **CORS_ORIGINS**: Warns if `*` is used in production; validates URL format
- **SESSION_TIMEOUT**: Must be between 1 minute and 7 days
- **LOG_LEVEL**: Must be a standard log level
- **MEMORY_BACKEND**: Must be a supported backend

On startup in production mode, security issues are logged as warnings.

### Environment Detection

Set `NODE_ENV=production` or `ENV=production` to enable production security checks.

## Docker

```bash
# Build
docker build -t masterclaw-core .

# Run
docker run -p 8000:8000 --env-file .env masterclaw-core
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=masterclaw_core

# Run specific test file
pytest tests/test_config.py -v
```

## Related

- [masterclaw-infrastructure](https://github.com/TheMasterClaw/masterclaw-infrastructure) — Deployment
- [masterclaw-tools](https://github.com/TheMasterClaw/masterclaw-tools) — CLI
- [MasterClawInterface](https://github.com/TheMasterClaw/MasterClawInterface) — The UI

---

*The brain behind the claw.* 🐾
