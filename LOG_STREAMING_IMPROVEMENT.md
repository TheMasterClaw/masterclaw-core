# Log Streaming Improvement Summary

## Overview
Added real-time log streaming capabilities to the MasterClaw ecosystem via Server-Sent Events (SSE), enabling both the web interface and CLI to stream logs without requiring the Loki monitoring stack.

## Components Modified

### 1. masterclaw-core (API)
**Files Changed:**
- `models.py` - Added `LogStreamRequest` and `LogEntry` Pydantic models
- `main.py` - Added SSE streaming endpoint and log query endpoint

**New Features:**
- `POST /v1/logs/stream` - Real-time log streaming via SSE
  - Service filtering (core, backend, gateway, etc.)
  - Log level filtering (DEBUG, INFO, WARNING, ERROR)
  - Full-text search within messages
  - Historical + live log aggregation
- `GET /v1/logs` - Non-streaming JSON log query
- In-memory circular log buffer (5000 entries)
- Support for both JSON and standard log format parsing

### 2. masterclaw-tools (CLI)
**Files Changed:**
- `lib/logs.js` - Added `stream` subcommand
- `README.md` - Updated documentation

**New Features:**
- `mc logs stream` - Stream logs in real-time
  - `--service <name>` - Filter by service
  - `--level <level>` - Filter by log level
  - `--search <pattern>` - Search within messages
  - `--since <duration>` - Include historical logs
  - `--no-follow` - Historical only, no streaming
  - `--json` - Raw JSON output
- Color-coded output by log level
- Graceful handling of connection errors

### 3. masterclaw-core (Documentation)
**Files Changed:**
- `README.md` - Added Logs API section

## Benefits

1. **No Dependencies** - Works without Loki monitoring stack
2. **Real-time** - Live log streaming via SSE
3. **Flexible Filtering** - Service, level, and text search
4. **Web-Ready** - SSE format works natively in browsers
5. **CLI Integration** - Color-coded, human-readable output

## Usage Examples

### CLI
```bash
# Stream all logs
mc logs stream

# Stream core service ERROR logs
mc logs stream --service core --level ERROR

# Search for database errors
mc logs stream --search "database" --level ERROR

# Historical only (no streaming)
mc logs stream --since 1h --no-follow
```

### API
```bash
# Stream via curl
curl -N -H "Accept: text/event-stream" \
     -H "Content-Type: application/json" \
     -X POST \
     -d '{"service": "core", "level": "INFO", "follow": true}' \
     http://localhost:8000/v1/logs/stream

# Get recent logs (JSON)
curl http://localhost:8000/v1/logs?service=core&level=ERROR&since=1h
```

## Technical Details

- **Protocol:** Server-Sent Events (SSE)
- **Buffer Size:** 5000 most recent log entries
- **Historical Range:** Configurable (default: last 5 minutes)
- **Log Formats:** JSON (structured) and standard text logs
- **Filtering:** Server-side to minimize bandwidth

## Commits

- `masterclaw_core`: `026845e` - feat(core): add real-time log streaming via SSE
- `masterclaw-tools`: `3c7b1b7` - feat(logs): add real-time log streaming CLI command
- `masterclaw-core`: `bddac37` - docs: add log streaming API documentation
