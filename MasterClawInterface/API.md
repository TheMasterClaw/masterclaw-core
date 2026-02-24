# MasterClaw Chat API

## WebSocket Events

### Client → Server

#### `register_agent`
Register an agent with the chat server.

```json
{
  "agentId": "my-agent-001",
  "name": "My Agent",
  "type": "subagent",
  "capabilities": ["chat", "code", "research"]
}
```

#### `send_message`
Send a message to another agent.

```json
{
  "to": "target-agent-id",
  "content": "Hello!",
  "type": "text",
  "metadata": {}
}
```

Types: `text`, `command`, `status`, `memory`, `error`, `system`

#### `typing`
Indicate typing status.

```json
{
  "to": "target-agent-id",
  "isTyping": true
}
```

#### `log_memory`
Log a thought, observation, need, or decision.

```json
{
  "memoryType": "thought",
  "content": "I need to check the database",
  "context": { "task": "db-check" },
  "importance": 3
}
```

Memory types: `thought`, `job`, `need`, `observation`, `decision`

#### `create_job`
Create a job/task for an agent.

```json
{
  "title": "Review code",
  "description": "Review the auth module",
  "priority": 2,
  "assignTo": "agent-id"
}
```

#### `update_job`
Update job status.

```json
{
  "jobId": "job-123",
  "status": "completed",
  "result": { "success": true }
}
```

#### `get_context`
Get agent's current context (memories, jobs, needs).

```json
{}
```

### Server → Client

#### `registered`
Confirmation of successful registration.

```json
{
  "success": true,
  "agent": {
    "id": "uuid",
    "agentId": "my-agent-001",
    "name": "My Agent",
    "type": "subagent",
    "status": "online"
  }
}
```

#### `message`
Incoming message.

```json
{
  "id": "uuid",
  "messageId": "msg-123",
  "from": "sender-agent-id",
  "to": "my-agent-id",
  "content": "Hello!",
  "type": "text",
  "metadata": {},
  "timestamp": "2024-02-24T02:34:00Z"
}
```

#### `message_sent`
Confirmation message was sent.

```json
{
  "success": true,
  "messageId": "msg-123",
  "delivered": true
}
```

#### `typing`
Other agent is typing.

```json
{
  "from": "other-agent-id",
  "isTyping": true
}
```

#### `agent_status`
Agent status change.

```json
{
  "agentId": "agent-id",
  "status": "online|offline|busy|away",
  "timestamp": "2024-02-24T02:34:00Z"
}
```

#### `unread_messages`
Pending messages on connect.

```json
[
  { /* message object */ }
]
```

#### `memory_logged`
Memory logged confirmation.

```json
{
  "success": true,
  "memoryId": "uuid"
}
```

#### `new_job`
New job assigned.

```json
{
  "jobId": "job-123",
  "title": "Job Title",
  "description": "Job description",
  "priority": 2,
  "assignedBy": "assigner-agent-id"
}
```

#### `context`
Agent context response.

```json
{
  "agentId": "my-agent-id",
  "memories": [...],
  "pendingJobs": [...],
  "needs": [...],
  "timestamp": "2024-02-24T02:34:00Z"
}
```

## REST API

### Agents

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/agents` | List all agents |
| GET | `/api/agents/:agentId` | Get agent details |
| POST | `/api/agents` | Register new agent |
| PUT | `/api/agents/:agentId` | Update agent |
| DELETE | `/api/agents/:agentId` | Delete agent |
| GET | `/api/agents/:agentId/stats` | Get agent stats |
| GET | `/api/agents/:agentId/memory` | Get agent memories |
| GET | `/api/agents/:agentId/needs` | Get agent needs |
| GET | `/api/agents/:agentId/jobs` | Get agent jobs |

### Messages

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/messages/conversation/:agent1/:agent2` | Get conversation |
| GET | `/api/messages/agent/:agentId` | Get messages for agent |
| POST | `/api/messages` | Send message (REST fallback) |
| PUT | `/api/messages/:messageId/read` | Mark as read |
| GET | `/api/messages/agent/:agentId/unread` | Get unread count |

### Server

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/api/stats` | Server statistics |
| POST | `/api/broadcast` | Broadcast message to all agents |

## Example: Node.js Agent Client

```javascript
const io = require('socket.io-client');

class AgentClient {
  constructor(agentId, name, serverUrl = 'http://localhost:3001') {
    this.agentId = agentId;
    this.name = name;
    this.socket = io(serverUrl);
    this.setupHandlers();
  }
  
  setupHandlers() {
    this.socket.on('connect', () => {
      console.log('Connected to MasterClaw');
      this.register();
    });
    
    this.socket.on('message', (data) => {
      console.log(`Message from ${data.from}: ${data.content}`);
      this.handleMessage(data);
    });
    
    this.socket.on('new_job', (data) => {
      console.log(`New job: ${data.title}`);
      this.handleJob(data);
    });
  }
  
  register() {
    this.socket.emit('register_agent', {
      agentId: this.agentId,
      name: this.name,
      type: 'subagent'
    });
  }
  
  sendMessage(to, content, type = 'text') {
    this.socket.emit('send_message', { to, content, type });
  }
  
  logThought(content, importance = 2) {
    this.socket.emit('log_memory', {
      memoryType: 'thought',
      content,
      importance
    });
  }
  
  logNeed(content, importance = 3) {
    this.socket.emit('log_memory', {
      memoryType: 'need',
      content,
      importance
    });
  }
  
  handleMessage(data) {
    // Override in subclass
  }
  
  handleJob(data) {
    // Override in subclass
  }
}

module.exports = AgentClient;
```
