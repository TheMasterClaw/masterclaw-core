# Changelog

All notable changes to MasterClaw Core will be documented in this file.

## [Unreleased]

### Added
- **Correlation ID System** - Distributed tracing for CLI operations
  - Unique correlation IDs generated for each command execution
  - IDs propagated through logger, audit log, and event systems
  - Environment variable `MC_CORRELATION_ID` for CI/CD integration
  - HTTP header `x-correlation-id` support for API calls
  - Child correlation IDs for sub-operations (hierarchical tracing)
  - Security: IDs validated and sanitized to prevent injection
  - New `lib/correlation.js` module with 66 comprehensive tests
  - `wrapCommandWithCorrelation()` for automatic command tracing
  - Enables end-to-end tracing of operations across log types
- **Event Tracking System (`mc events`)** - Centralized event tracking and notification history
  - `mc events list` — List events with filtering by type, severity, source, and time
  - `mc events show <id>` — Display detailed event information
  - `mc events ack <id>` — Acknowledge individual events
  - `mc events ack-all` — Bulk acknowledge events
  - `mc events stats` — Event statistics and summaries
  - `mc events add <title>` — Add custom events
  - `mc events export` — Export events to JSON or CSV
  - `mc events watch` — Real-time event monitoring
  - Event types: backup, deploy, alert, error, warning, info, security, maintenance, restore, update
  - Severity levels: critical, high, medium, low, info
  - Automatic event creation from other commands (backup, deploy, restore)
- **Error Handler JSON Output Mode** - Structured JSON error output for production/CI environments
  - Set `MC_JSON_OUTPUT=1` to enable machine-readable error output
  - Structured JSON schema with timestamp, category, exit code, message, and error details
  - Sensitive data automatically masked in JSON output
  - Useful for log aggregation (ELK, Splunk, cloud logging) and CI/CD pipelines
  - Global error handlers (unhandled rejections, uncaught exceptions) also support JSON mode
- **Chat Command Security Hardening** - Enhanced security for `mc chat` command
  - Input validation: max length (10,000 chars), line count limits, dangerous pattern detection
  - XSS protection: blocks script tags, event handlers, javascript: URLs, data:text/html
  - Input sanitization: removes control characters, ANSI escapes, suspicious Unicode
  - Rate limiting: 20 messages per minute per user
  - Sensitive data masking for audit logs
  - New `lib/chat-security.js` module with comprehensive security utilities
  - 55 test cases covering validation, sanitization, and risk analysis
- **Config Command Module (`mc config`)** - Complete configuration management for CLI
  - `mc config list` — Display all configuration values with security masking
  - `mc config get <key>` — Retrieve specific values using dot notation
  - `mc config set <key> <value>` — Update configuration with type inference
  - `mc config export [file]` — Export config to JSON with sensitive value masking
  - `mc config import <file>` — Import config with diff preview and dry-run support
  - `mc config reset` — Reset to defaults with confirmation protection
  - Security features: rate limiting, sensitive value masking, prototype pollution protection
- **Security Auto-Responder Path Fallback** - Improved error handling for file system operations
  - Automatic fallback to alternate paths when default paths aren't writable
  - Graceful handling of permission errors with informative logging
  - Path information included in statistics for better observability
  - System continues to function in-memory when persistence fails
  - New tests for permission error scenarios
- **Batch Memory Import/Export API** - Efficient bulk memory operations
  - `POST /v1/memory/batch` - Import up to 1000 memories in a single request
    - Skip duplicate detection based on content hash
    - Source prefix for tracking import origin
    - Detailed import report with success/failure counts
  - `POST /v1/memory/export` - Export memories with flexible filtering
    - Semantic search query filtering
    - Metadata, source, and date range filters
    - Up to 5000 memories per export request
  - New Pydantic models: `BatchMemoryImportRequest`, `BatchMemoryImportResponse`, `MemoryExportRequest`, `MemoryExportResponse`
  - Complements existing single-memory endpoints for migration and backup workflows
- **Tool Use Framework** - Comprehensive tool calling system for AI agents
  - `GET /v1/tools` - List all available tools with their definitions
  - `GET /v1/tools/{tool_name}` - Get detailed information about a specific tool
  - `POST /v1/tools/execute` - Execute a tool with provided parameters
  - `GET /v1/tools/definitions/openai` - Get tools in OpenAI function format
  - **GitHub Tool** - Full GitHub API integration (repos, issues, PRs, comments)
  - **System Tool** - Safe system commands and information (with security restrictions)
  - **Weather Tool** - Weather data via Open-Meteo API (no API key required)
  - Extensible registry for adding custom tools
  - Parameter validation and type checking
  - Security controls for dangerous operations
- **Interactive API Documentation** - Auto-generated docs with Swagger UI and ReDoc
  - Swagger UI at `/docs` - Interactive API explorer with "Try it out" feature
  - ReDoc at `/redoc` - Clean, responsive API reference documentation  
  - OpenAPI 3.0 schema at `/openapi.json` - Machine-readable specification
  - Categorized endpoints with descriptions for better navigation
  - Enhanced root endpoint (`/`) with documentation URLs
- **Analytics API Endpoints** - Expose usage metrics and statistics
  - `GET /v1/analytics` - Analytics system summary and available metrics
  - `GET/POST /v1/analytics/stats` - Usage statistics (requests, chats, tokens, error rates)
  - Automatic tracking of API requests with timing and status codes
  - Chat usage tracking by provider and model
  - Memory search performance metrics
  - Configurable lookback period (1-90 days)
- **WebSocket Streaming Chat Endpoint** (`/v1/chat/stream/{session_id}`)
  - Real-time token-by-token streaming for chat responses
  - Support for both OpenAI and Anthropic providers
  - Integrated memory retrieval for contextual responses
  - Comprehensive error handling with typed error codes
  - Automatic conversation storage to memory
  - Bidirectional JSON message protocol

### Changed
- Updated root endpoint (`/`) to include new WebSocket and Analytics endpoints
- Chat and memory endpoints now track analytics automatically
- Enhanced API metadata with detailed descriptions and authentication info
- **Security**: Improved `security_response.py` with graceful file permission error handling
  - Added `_ensure_writable_path()` method with automatic fallback logic
  - Enhanced `_save_blocklist()` and `_save_rules()` with specific error handling
  - Updated `get_stats()` to include path information for debugging

## [0.1.0] - 2026-02-13

### Added
- Initial release of MasterClaw Core
- REST API with chat completion endpoint (`/v1/chat`)
- Memory management with semantic search
- WebSocket connection manager (infrastructure only)
- Support for OpenAI and Anthropic LLM providers
- Health check endpoint (`/health`)

---

*Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)*
