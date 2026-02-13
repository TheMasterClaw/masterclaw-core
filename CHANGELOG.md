# Changelog

All notable changes to MasterClaw Core will be documented in this file.

## [Unreleased]

### Added
- **WebSocket Streaming Chat Endpoint** (`/v1/chat/stream/{session_id}`)
  - Real-time token-by-token streaming for chat responses
  - Support for both OpenAI and Anthropic providers
  - Integrated memory retrieval for contextual responses
  - Comprehensive error handling with typed error codes
  - Automatic conversation storage to memory
  - Bidirectional JSON message protocol

### Changed
- Updated root endpoint (`/`) to include new WebSocket endpoint in the API documentation

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
