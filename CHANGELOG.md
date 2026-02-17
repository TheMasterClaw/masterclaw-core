# Changelog

All notable changes to MasterClaw Core will be documented in this file.

## [Unreleased]

### Added
- **Config Command Module (`mc config`)** - Complete configuration management for CLI
  - `mc config list` — Display all configuration values with security masking
  - `mc config get <key>` — Retrieve specific values using dot notation
  - `mc config set <key> <value>` — Update configuration with type inference
  - `mc config export [file]` — Export config to JSON with sensitive value masking
  - `mc config import <file>` — Import config with diff preview and dry-run support
  - `mc config reset` — Reset to defaults with confirmation protection
  - Security features: rate limiting, sensitive value masking, prototype pollution protection
- **Unified Maintenance Command (`mc maintenance`)** - Comprehensive system maintenance workflow
  - Health checks for Core API, disk space, and session statistics
  - Automated session cleanup with configurable retention periods
  - Backup verification with freshness checking
  - Docker system pruning for images, containers, and volumes
  - Optional log cleanup for container logs
  - Report generation for audit trails (`--report` flag)
  - Scheduling helper with cron examples (`mc maintenance schedule`)
  - Quick status check (`mc maintenance status`)
  - Non-interactive mode for automation (`--force` flag)
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

### Fixed
- Fixed syntax error in doctor.js (quote escaping in awk command)
- Fixed missing command name in notify.js causing addCommand error

### Changed
- Updated root endpoint (`/`) to include new WebSocket and Analytics endpoints
- Chat and memory endpoints now track analytics automatically
- Enhanced API metadata with detailed descriptions and authentication info

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
