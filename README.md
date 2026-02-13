# MasterClaw Core 🧠

The AI brain — LLM integrations, memory systems, agent orchestration, and tool handlers.

## Overview

This is the intelligence layer that powers MasterClaw. It handles:

- **LLM Integration** — OpenAI, Anthropic, local models
- **Memory Systems** — Short-term context, long-term embeddings
- **Agent Orchestration** — Multi-step reasoning, tool use
- **Tool Handlers** — Extensible tool system

## Architecture

```
┌─────────────────────────────────────────┐
│  API Layer (FastAPI)                    │
├─────────────────────────────────────────┤
│  Agent Orchestrator                     │
├─────────────────────────────────────────┤
│  LLM Router (OpenAI, Anthropic, Local)  │
├─────────────────────────────────────────┤
│  Memory Store (Embeddings + Vector DB)  │
├─────────────────────────────────────────┤
│  Tool Registry                          │
└─────────────────────────────────────────┘
```

## Quick Start

```bash
# Install
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your API keys

# Run
python -m masterclaw_core
```

## API

### Chat
```bash
POST /v1/chat
{
  "message": "What did we discuss yesterday?",
  "session_id": "abc123"
}
```

### Memory Search
```bash
POST /v1/memory/search
{
  "query": "backup strategy",
  "top_k": 5
}
```

### Tool Call
```bash
POST /v1/tools/execute
{
  "tool": "github",
  "action": "create_issue",
  "params": {...}
}
```

## Related Repos

- [masterclaw-interface](https://github.com/TheMasterClaw/MasterClawInterface) — The UI
- [masterclaw-infrastructure](https://github.com/TheMasterClaw/masterclaw-infrastructure) — Deployment
- [masterclaw-tools](https://github.com/TheMasterClaw/masterclaw-tools) — CLI utilities
- [rex-deus](https://github.com/TheMasterClaw/rex-deus) — Personal configs (private)
- [level100-studios](https://github.com/TheMasterClaw/level100-studios) — Parent org

---

*The brain behind the claw.* 🐾
