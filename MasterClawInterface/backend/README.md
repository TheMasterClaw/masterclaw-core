# MasterClaw Interface Backend

Real-time multi-agent communication server with WebSocket support, agent memory tracking, and job management.

## Features

- **WebSocket-based real-time communication** between agents
- **REST API** for agent management and message history
- **Agent memory tracking**: thoughts, jobs, desires, blockers
- **Job management**: create, assign, track job status
- **In-memory database** for development (PostgreSQL for production)

## Quick Start

```bash
# Install dependencies
npm install

# Start server (uses in-memory database by default)
npm start

# Or with nodemon for development
npm run dev
```

Server runs on `http://localhost:3001`

## Environment Variables

```env
PORT=3001
NODE_ENV=development
USE_MEMORY_DB=true                    # Use in-memory DB (set to false for PostgreSQL)
DATABASE_URL=postgresql://...         # PostgreSQL connection string
JWT_SECRET=your-secret
WS_HEARTBEAT_INTERVAL=30000
AGENT_TIMEOUT=60000
```

## API Endpoints

### Agents
- `GET /api/agents` - List all agents
- `POST /api/agents` - Register new agent
- `GET /api/agents/:agentId` - Get agent details
- `PUT /api/agents/:agentId` - Update agent
- `DELETE /api/agents/:agentId` - Delete agent
- `GET /api/agents/:agentId/memory` - Get agent memories
- `POST /api/agents/:agentId/memory` - Log memory (thought/need/observation)
- `GET /api/agents/:agentId/jobs` - Get agent jobs
- `POST /api/agents/:agentId/jobs` - Create job for agent
- `PUT /api/agents/:agentId/jobs/:jobId` - Update job status
- `GET /api/agents/:agentId/needs` - Get agent needs/desires
- `GET /api/agents/:agentId/stats` - Get agent statistics

### Messages
- `GET /api/messages/agent/:agentId` - Get messages for agent
- `POST /api/messages` - Send message (REST fallback)
- `GET /api/messages/conversation/:agent1/:agent2` - Get conversation

### Server
- `GET /health` - Health check
- `GET /api/stats` - Server statistics
- `POST /api/broadcast` - Broadcast message to all agents

## WebSocket Events

### Client → Server
- `register_agent` - Register an agent
- `send_message` - Send message to another agent
- `typing` - Typing indicator
- `heartbeat` - Keep connection alive
- `log_memory` - Log thought/memory
- `create_job` - Create job/task
- `update_job` - Update job status
- `get_context` - Get agent context

### Server → Client
- `registered` - Registration confirmed
- `message` - Incoming message
- `message_sent` - Message delivery confirmation
- `typing` - Other agent typing
- `agent_status` - Agent status change
- `memory_logged` - Memory logged confirmation
- `new_job` - New job assigned
- `job_updated` - Job status updated
- `context` - Agent context response
- `unread_messages` - Pending messages on connect

## Example Usage

### Register an Agent
```javascript
const io = require('socket.io-client');
const socket = io('http://localhost:3001');

socket.on('connect', () => {
  socket.emit('register_agent', {
    agentId: 'my-agent-001',
    name: 'My Agent',
    type: 'subagent',
    capabilities: ['chat', 'code']
  });
});

socket.on('registered', (data) => {
  console.log('Registered:', data);
});
```

### Send a Message
```javascript
socket.emit('send_message', {
  to: 'other-agent-id',
  content: 'Hello!',
  type: 'text'
});
```

### Log a Thought
```javascript
socket.emit('log_memory', {
  memoryType: 'thought',
  content: 'I need to check the database',
  importance: 2
});
```

### Create a Job
```javascript
socket.emit('create_job', {
  title: 'Review code',
  description: 'Review the auth module',
  priority: 2,
  assignTo: 'agent-id'
});
```

## Architecture

```
backend/
├── server.js              # Main entry point
├── src/
│   ├── config/           # Configuration
│   │   ├── config.js     # Environment config
│   │   ├── database.js   # Database router
│   │   ├── database-memory.js  # In-memory implementation
│   │   └── database-pg.js      # PostgreSQL implementation
│   ├── models/           # Database models
│   │   ├── Agent.js
│   │   ├── Message.js
│   │   ├── AgentMemory.js
│   │   ├── AgentJob.js
│   │   └── schema.js
│   ├── routes/           # REST API routes
│   │   ├── agents.js
│   │   └── messages.js
│   ├── websocket/        # WebSocket handlers
│   │   └── server.js
│   └── middleware/       # Express middleware
│       └── logger.js
```

## Testing

```bash
# Run all API tests
curl -s http://localhost:3001/health

# Create an agent
curl -X POST http://localhost:3001/api/agents \
  -H "Content-Type: application/json" \
  -d '{"agentId":"test-001","name":"Test Agent"}'

# Get agent details
curl http://localhost:3001/api/agents/test-001

# Send message
curl -X POST http://localhost:3001/api/messages \
  -H "Content-Type: application/json" \
  -d '{"fromAgent":"test-001","toAgent":"test-002","content":"Hello!"}'
```