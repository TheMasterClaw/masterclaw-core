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
├── config.py          # Settings
├── models.py          # Pydantic models
├── llm.py             # LLM router (OpenAI, Anthropic)
└── memory.py          # Memory store (Chroma, JSON)
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | - | OpenAI API key |
| `ANTHROPIC_API_KEY` | - | Anthropic API key |
| `DEFAULT_MODEL` | gpt-4 | Default LLM model |
| `MEMORY_BACKEND` | chroma | Memory backend (chroma/json) |
| `CHROMA_PERSIST_DIR` | ./data/chroma | ChromaDB directory |
| `PORT` | 8000 | API port |

## Docker

```bash
# Build
docker build -t masterclaw-core .

# Run
docker run -p 8000:8000 --env-file .env masterclaw-core
```

## Related

- [masterclaw-infrastructure](https://github.com/TheMasterClaw/masterclaw-infrastructure) — Deployment
- [masterclaw-tools](https://github.com/TheMasterClaw/masterclaw-tools) — CLI
- [MasterClawInterface](https://github.com/TheMasterClaw/MasterClawInterface) — The UI

---

*The brain behind the claw.* 🐾
