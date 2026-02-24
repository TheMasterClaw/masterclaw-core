# MasterClaw Interface - Project Tracking

## 🎯 Mission
Build a real-time chat interface so Rex can talk directly to any agent in the swarm.

## 📁 Location
`TheMasterClaw/masterclaw-core/MasterClawInterface/`

## 🏗 Architecture

```
MasterClawInterface/
├── backend/           # WebSocket server + API
│   ├── server.js      # Express + Socket.io
│   ├── routes/        # REST API routes
│   ├── models/        # Database models
│   └── websocket/     # Socket handlers
├── frontend/          # React chat UI
│   ├── src/
│   │   ├── components/  # Chat components
│   │   ├── pages/       # Main views
│   │   └── context/     # WebSocket context
│   └── package.json
├── shared/            # Shared types/utils
└── README.md
```

## 👥 Team Assignments

### Phase 1 - Foundation ✅
| Agent | Role | Status |
|-------|------|--------|
| masterclaw-core-agent | Core Architecture | ✅ **DONE** - agent_chat.py with memory system |

### Phase 2 - Build 🚧
| Agent | Role | Status |
|-------|------|--------|
| interface-frontend-builder | React UI | 🚧 Building components |
| interface-backend-builder | Express API | 🚧 Building server |
| sub-7-devops | Docker + Deploy | ⏳ Queued |
| sub-8-security | Auth | ⏳ Queued |
| sub-5-qa | Tests | ⏳ Queued |

### Supporting Team
| Agent | Role | Focus |
|-------|------|-------|
| sub-2-backend | Backend API | WebSocket server, REST API |
| sub-1-frontend | Frontend UI | React chat interface |
| sub-3-fullstack | Integration | End-to-end connections |
| sub-4-content | Docs | README, API docs |

## ✅ What's Built

### Core Architecture (`agent_chat.py`)
- ✅ AgentJob tracking (pending/in_progress/completed/failed)
- ✅ AgentDesire tracking (agent needs/wants)
- ✅ AgentBlocker tracking (what's blocking agents)
- ✅ Message type system (user_message, agent_message, system)
- ✅ Agent status tracking (online/busy/away/offline/error)
- ✅ Swarm coordination (formed/disbanded/handoff)

### Project Structure
- ✅ package.json (frontend & backend)
- ✅ PROJECT.md (this file)

## 🚀 Features Required

### Core (MVP)
- [ ] Express server with Socket.io
- [ ] React frontend components
- [ ] Agent registry (list all agents)
- [ ] Message routing (Rex → Agent)
- [ ] Chat UI (message threads)
- [ ] Real-time updates

### Advanced
- [x] Agent memory logging (jobs/desires/blockers)
- [ ] Message persistence (PostgreSQL)
- [ ] Agent status display
- [ ] File attachments
- [ ] Message search
- [ ] Authentication (JWT)

## 🛠 Tech Stack

- **Backend:** Node.js, Express, Socket.io, PostgreSQL, Redis
- **Frontend:** React, Tailwind CSS, Socket.io-client
- **Auth:** JWT tokens
- **Deploy:** Vercel (frontend), Railway (backend)

## 📚 References

- github.com/kyegomez/swarms
- github.com/youseai/openai-swarm-node
- github.com/ruvnet/claude-flow

## 📝 Status

**Started:** 2026-02-24
**Updated:** 2026-02-24 03:15 UTC
**Phase:** Phase 2 - Building frontend & backend
**Target:** Deployable MVP by end of day

## 🔗 API Endpoints (Draft)

```
GET    /api/agents           # List all agents
GET    /api/agents/:id       # Get agent details
GET    /api/agents/:id/messages  # Message history
POST   /api/messages         # Send message
GET    /api/agents/:id/memory   # Jobs/desires/blockers
WS     /ws                   # WebSocket connection
```

## 🎨 WebSocket Events

```javascript
// Client → Server
'join', { agentId }
'message', { to, content }
'typing', { agentId }
'update_memory', { type, data }

// Server → Client  
'agent:joined', { agentId, status }
'agent:status', { agentId, status }
'message', { from, content, timestamp }
'agent:typing', { agentId }
'memory:updated', { agentId, type, data }
```

## 📦 Database Schema

```sql
-- Agents
agents (id, name, status, created_at)

-- Messages
messages (id, from_agent, to_agent, content, timestamp)

-- Agent Memory
agent_jobs (id, agent_id, title, status, started_at, completed_at)
agent_desires (id, agent_id, description, priority, created_at)
agent_blockers (id, agent_id, description, severity, created_at, resolved_at)
```

## 🚀 Deployment

### Frontend (Vercel)
```bash
cd frontend
vercel --prod
```

### Backend (Railway)
```bash
cd backend
railway up
```
