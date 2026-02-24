# MasterClaw Chat Interface

🔴 **CRITICAL INFRASTRUCTURE** - Rex-to-Agent Communication System

A real-time chat interface for Rex Deus to communicate directly with the MasterClaw agent fleet.

## 🚀 Features

- **Real-time Messaging** - WebSocket-based bidirectional communication
- **Agent Registry** - Dynamic agent management with 7 specialized agents
- **Message Routing** - Direct Rex → Agent message routing
- **Agent Memory System** - Logs thoughts, jobs, and needs per agent
- **React Chat UI** - Modern dark-themed interface

## 📁 Structure

```
MasterClawInterface/
├── backend/
│   └── src/
│       └── server.js          # WebSocket server + API
├── frontend/
│   └── src/
│       ├── App.jsx            # Main chat interface
│       ├── index.css          # Dark theme styles
│       └── main.jsx           # React entry
└── package.json
```

## 🛠️ Quick Start

```bash
# Install dependencies
cd MasterClawInterface
npm install
cd frontend && npm install && cd ..

# Start backend
npm run dev

# Start frontend (new terminal)
cd frontend
npm run dev
```

Access at: http://localhost:5173

## 🌐 WebSocket Events

| Event | Direction | Description |
|-------|-----------|-------------|
| `register-rex` | Client → Server | Register as Rex |
| `register-agent` | Client → Server | Register an agent |
| `send-message` | Client → Server | Send direct message |
| `broadcast` | Client → Server | Broadcast to all agents |
| `message` | Server → Client | Receive message |
| `agent-status` | Server → Client | Agent online/offline |

## 🧠 Agent Memory

Each agent has persistent memory for:
- **Thoughts** - Internal reasoning logs
- **Jobs** - Active tasks with status tracking
- **Needs** - Resource requests or dependencies

## 👥 Agent Fleet

| ID | Name | Role | Capabilities |
|----|------|------|--------------|
| agent-research | Research Agent | research | web_search, data_analysis |
| agent-coding | Coding Agent | coding | code_gen, debugging |
| agent-devops | DevOps Agent | devops | cicd, cloud |
| agent-security | Security Agent | security | vuln_scan, compliance |
| agent-qa | QA Agent | qa | testing, bug_tracking |
| agent-content | Content Agent | content | writing, editing |
| agent-orchestrator | Orchestrator | orchestrator | coordination, routing |

---
**Status:** ✅ OPERATIONAL
