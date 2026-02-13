# Changelog

All notable changes to MasterClaw Core will be documented in this file.

## [Unreleased]

### Added
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
