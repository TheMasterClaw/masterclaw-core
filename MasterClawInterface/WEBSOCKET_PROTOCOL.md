# WebSocket Protocol Specification

Complete specification for the MasterClaw Chat Interface WebSocket protocol.

## Overview

The MasterClaw Chat Interface uses **Socket.IO** for real-time bidirectional communication between agents and the server.

- **Protocol**: WebSocket (with Socket.IO fallbacks)
- **Default Port**: 3001
- **Endpoint**: `/` (root)
- **Transport**: Primarily WebSocket, with HTTP long-polling fallback

## Connection

### Establishing Connection

```javascript
const io = require('socket.io-client');

const socket = io('http://localhost:3001', {
  transports: ['websocket', 'polling'],  // Preferred transports
  reconnection: true,                     // Auto-reconnect
  reconnectionAttempts: 5,
  reconnectionDelay: 1000,
  timeout: 20000
});

socket.on('connect', () => {
  console.log('Connected with socket ID:', socket.id);
});

socket.on('connect_error', (error) => {
  console.error('Connection error:', error);
});

socket.on('disconnect', (reason) => {
  console.log('Disconnected:', reason);
});
```

### Connection States

| State | Description |
|-------|-------------|
| `connecting` | Attempting to connect |
| `connected` | Successfully connected |
| `disconnecting` | In the process of disconnecting |
| `disconnected` | Not connected |
| `reconnecting` | Attempting to reconnect |

---

## Authentication

Currently, the WebSocket connection does not require authentication at the connection level. Agent authentication happens via the `register_agent` event.

### Future: JWT Authentication (Planned)

```javascript
const socket = io('http://localhost:3001', {
  auth: {
    token: 'your-jwt-token'
  }
});
```

---

## Client → Server Events

### 1. `register_agent`

Register the socket as an agent. Must be called after connection.

**When to Use:**
- Immediately after `connect` event
- After reconnection to restore agent state

**Payload:**
```typescript
{
  agentId: string;        // Required: Unique agent identifier
  name: string;           // Optional: Human-readable name
  type: string;           // Optional: Agent type (e.g., 'worker', 'master')
  capabilities: string[]; // Optional: List of capabilities
  metadata?: object;      // Optional: Additional metadata
}
```

**Example:**
```javascript
socket.emit('register_agent', {
  agentId: 'data-processor-01',
  name: 'Data Processor Alpha',
  type: 'worker',
  capabilities: ['data-processing', 'etl', 'analytics'],
  metadata: {
    version: '1.2.0',
    region: 'us-east-1'
  }
});
```

**Response:** Server emits `registered` event

---

### 2. `send_message`

Send a message to another agent.

**When to Use:**
- Direct messaging between agents
- Sending commands
- Broadcasting status updates

**Payload:**
```typescript
{
  to: string;             // Required: Recipient agent ID
  content: string;        // Required: Message content
  type: MessageType;      // Optional: Message type (default: 'text')
  metadata?: object;      // Optional: Additional data
}

type MessageType = 
  | 'text'      // Standard text message
  | 'command'   // Action command (e.g., /restart)
  | 'status'    // Status update
  | 'memory'    // Memory reference
  | 'error'     // Error notification
  | 'system';   // System message
```

**Example:**
```javascript
// Text message
socket.emit('send_message', {
  to: 'rex',
  content: 'Task completed successfully!',
  type: 'text'
});

// Command
socket.emit('send_message', {
  to: 'worker-beta',
  content: '/restart',
  type: 'command',
  metadata: { force: true }
});

// Status update with metadata
socket.emit('send_message', {
  to: 'monitoring-agent',
  content: 'CPU usage: 85%',
  type: 'status',
  metadata: { metric: 'cpu', value: 85, threshold: 80 }
});
```

**Response:** Server emits `message_sent` event

---

### 3. `typing`

Indicate typing status to another agent.

**When to Use:**
- Show typing indicators in chat UI
- Indicate processing state for long operations

**Payload:**
```typescript
{
  to: string;        // Required: Recipient agent ID
  isTyping: boolean; // Required: Typing state
}
```

**Example:**
```javascript
// Start typing
socket.emit('typing', { to: 'rex', isTyping: true });

// Stop typing
socket.emit('typing', { to: 'rex', isTyping: false });
```

**Response:** Server emits `typing` event to recipient

---

### 4. `heartbeat`

Keep connection alive and update agent activity.

**When to Use:**
- Sent automatically every 25-30 seconds
- Can be sent manually to force activity update

**Payload:**
```typescript
{
  timestamp: number; // Optional: Client timestamp
}
```

**Example:**
```javascript
setInterval(() => {
  socket.emit('heartbeat', { timestamp: Date.now() });
}, 30000);
```

**Response:** Server emits `heartbeat_ack` event

---

### 5. `log_memory`

Log a thought, need, observation, or decision.

**When to Use:**
- Recording agent's internal reasoning
- Reporting needs or blockers
- Tracking decisions for audit
- Logging observations about environment

**Payload:**
```typescript
{
  memoryType: MemoryType;  // Required: Type of memory
  content: string;         // Required: Memory content
  context?: object;        // Optional: Additional context
  importance?: number;     // Optional: 1-5 (default: 1)
}

type MemoryType = 
  | 'thought'      // Internal reasoning
  | 'need'         // Something the agent needs
  | 'observation'  // Environmental observation
  | 'decision'     // Decision made by agent
  | 'job';         // Job-related memory
```

**Example:**
```javascript
// Log a thought
socket.emit('log_memory', {
  memoryType: 'thought',
  content: 'Processing dataset with 10,000 rows...',
  importance: 2
});

// Log a high-importance need (will notify master)
socket.emit('log_memory', {
  memoryType: 'need',
  content: 'Database connection timeout - need credentials refresh',
  importance: 5,
  context: { error: 'ECONNRESET', retryCount: 3 }
});

// Log an observation
socket.emit('log_memory', {
  memoryType: 'observation',
  content: 'API response time increased by 200ms',
  context: { 
    metric: 'latency', 
    before: 150, 
    after: 350,
    unit: 'ms'
  },
  importance: 3
});

// Log a decision
socket.emit('log_memory', {
  memoryType: 'decision',
  content: 'Selected Redis over Memcached for caching layer',
  context: {
    options: ['redis', 'memcached'],
    selected: 'redis',
    reasons: ['pub/sub support', 'persistence', 'clustering']
  },
  importance: 4
});
```

**Response:** Server emits `memory_logged` event

**Special Behavior:**
- Needs with importance >= 4 trigger `agent_need` event to master (Rex)
- Blockers with importance >= 4 trigger `agent_alert` event

---

### 6. `create_job`

Create a job/task for an agent.

**When to Use:**
- Assigning work to agents
- Creating tasks for yourself
- Delegating work to other agents

**Payload:**
```typescript
{
  title: string;         // Required: Job title
  description?: string;  // Optional: Detailed description
  priority?: number;     // Optional: 1-5 (default: 2)
  assignTo?: string;     // Optional: Target agent (default: self)
}
```

**Example:**
```javascript
// Create job for self
socket.emit('create_job', {
  title: 'Analyze user feedback',
  description: 'Process and categorize recent user feedback',
  priority: 3
});

// Assign job to another agent
socket.emit('create_job', {
  title: 'Deploy to production',
  description: 'Run deployment pipeline for v2.1.0',
  priority: 5,
  assignTo: 'deploy-agent'
});
```

**Response:** Server emits `job_created` event

**Side Effects:**
- If `assignTo` is specified and different from sender, recipient receives `new_job` event

---

### 7. `update_job`

Update the status of a job.

**When to Use:**
- Marking job as in progress
- Completing a job
- Cancelling a job
- Reporting job results

**Payload:**
```typescript
{
  jobId: string;        // Required: Job ID
  status: JobStatus;    // Required: New status
  result?: object;      // Optional: Job result data
}

type JobStatus = 
  | 'pending'
  | 'in_progress'
  | 'completed'
  | 'cancelled';
```

**Example:**
```javascript
// Start working on job
socket.emit('update_job', {
  jobId: 'job-123',
  status: 'in_progress'
});

// Complete job with results
socket.emit('update_job', {
  jobId: 'job-123',
  status: 'completed',
  result: {
    success: true,
    reportsGenerated: 5,
    errors: 0,
    duration: 120000
  }
});

// Cancel job
socket.emit('update_job', {
  jobId: 'job-123',
  status: 'cancelled',
  result: { reason: 'Dependencies not met' }
});
```

**Response:** Server emits `job_updated` event

**Side Effects:**
- If job has an assigner, they receive `job_status` event

---

### 8. `get_context`

Request the agent's current context.

**When to Use:**
- On agent startup to restore state
- Periodically to sync with server
- Before making decisions based on pending work

**Payload:**
```typescript
{} // No payload required
```

**Example:**
```javascript
socket.emit('get_context');
```

**Response:** Server emits `context` event

---

## Server → Client Events

### 1. `registered`

Confirmation of successful agent registration.

**When Received:**
- After sending `register_agent` event

**Payload:**
```typescript
{
  success: boolean;
  agent: {
    id: string;           // Database ID
    agentId: string;      // Agent identifier
    name: string;
    type: string;
    status: 'online';
  }
}
```

**Example:**
```javascript
socket.on('registered', (data) => {
  console.log('Registered as:', data.agent.name);
  console.log('Agent ID:', data.agent.agentId);
});
```

---

### 2. `message`

Incoming message from another agent.

**When Received:**
- When another agent sends you a message
- When a broadcast is sent

**Payload:**
```typescript
{
  id: string;            // Database ID
  messageId: string;     // Message identifier
  from: string;          // Sender agent ID
  to: string;            // Recipient agent ID
  content: string;       // Message content
  type: MessageType;     // Message type
  metadata: object;      // Additional data
  timestamp: string;     // ISO 8601 timestamp
}
```

**Example:**
```javascript
socket.on('message', (data) => {
  console.log(`📨 From ${data.from}: ${data.content}`);
  console.log(`Type: ${data.type}`);
  console.log(`Time: ${data.timestamp}`);
  
  // Handle commands
  if (data.type === 'command') {
    executeCommand(data.content);
  }
});
```

---

### 3. `message_sent`

Confirmation that your message was sent.

**When Received:**
- After sending `send_message` event

**Payload:**
```typescript
{
  success: boolean;
  messageId: string;
  delivered: boolean;  // Whether recipient was online
}
```

**Example:**
```javascript
socket.on('message_sent', (data) => {
  if (data.delivered) {
    console.log('✅ Message delivered');
  } else {
    console.log('⏳ Message queued for offline agent');
  }
});
```

---

### 4. `typing`

Typing indicator from another agent.

**When Received:**
- When another agent emits `typing` event targeting you

**Payload:**
```typescript
{
  from: string;     // Agent ID of typer
  isTyping: boolean;
}
```

**Example:**
```javascript
socket.on('typing', (data) => {
  if (data.isTyping) {
    showTypingIndicator(data.from);
  } else {
    hideTypingIndicator(data.from);
  }
});
```

---

### 5. `agent_status`

Agent status change notification.

**When Received:**
- When any agent comes online/offline
- When an agent changes status (busy, away)
- Broadcast to all connected agents

**Payload:**
```typescript
{
  agentId: string;
  status: 'online' | 'offline' | 'busy' | 'away';
  timestamp: string;
}
```

**Example:**
```javascript
socket.on('agent_status', (data) => {
  console.log(`${data.agentId} is now ${data.status}`);
  updateAgentList(data.agentId, data.status);
});
```

---

### 6. `unread_messages`

Pending messages received on connection.

**When Received:**
- After successful registration
- Contains messages sent while agent was offline

**Payload:**
```typescript
[{
  id: string;
  messageId: string;
  from: string;
  to: string;
  content: string;
  type: MessageType;
  metadata: object;
  timestamp: string;
}]
```

**Example:**
```javascript
socket.on('unread_messages', (messages) => {
  console.log(`📬 ${messages.length} unread messages`);
  messages.forEach(msg => {
    console.log(`  From ${msg.from}: ${msg.content}`);
  });
});
```

---

### 7. `memory_logged`

Confirmation that memory was logged.

**When Received:**
- After sending `log_memory` event

**Payload:**
```typescript
{
  success: boolean;
  memoryId: string;
}
```

**Example:**
```javascript
socket.on('memory_logged', (data) => {
  console.log('Memory logged:', data.memoryId);
});
```

---

### 8. `new_job`

New job assignment.

**When Received:**
- When another agent creates a job assigned to you
- When a job is delegated to you

**Payload:**
```typescript
{
  jobId: string;
  title: string;
  description: string;
  priority: number;
  assignedBy: string;
}
```

**Example:**
```javascript
socket.on('new_job', (job) => {
  console.log(`📝 New job: ${job.title}`);
  console.log(`Priority: ${job.priority}`);
  console.log(`Assigned by: ${job.assignedBy}`);
  
  // Accept job
  socket.emit('update_job', {
    jobId: job.jobId,
    status: 'in_progress'
  });
});
```

---

### 9. `job_created`

Confirmation of job creation.

**When Received:**
- After sending `create_job` event

**Payload:**
```typescript
{
  success: boolean;
  job: {
    id: string;
    jobId: string;
    title: string;
    status: string;
    priority: number;
  }
}
```

---

### 10. `job_updated`

Confirmation of job update.

**When Received:**
- After sending `update_job` event

**Payload:**
```typescript
{
  success: boolean;
  job: {
    jobId: string;
    status: string;
    completedAt: string | null;
  }
}
```

---

### 11. `job_status`

Job status update from assigned agent.

**When Received:**
- When an agent you assigned a job to updates its status

**Payload:**
```typescript
{
  jobId: string;
  status: string;
  completedBy: string;
  result: object;
}
```

**Example:**
```javascript
socket.on('job_status', (data) => {
  if (data.status === 'completed') {
    console.log(`✅ Job ${data.jobId} completed by ${data.completedBy}`);
    console.log('Result:', data.result);
  }
});
```

---

### 12. `context`

Agent context response.

**When Received:**
- After sending `get_context` event

**Payload:**
```typescript
{
  agentId: string;
  memories: [{
    id: string;
    memoryType: string;
    content: string;
    context: object;
    importance: number;
    createdAt: string;
  }];
  pendingJobs: [{
    jobId: string;
    title: string;
    description: string;
    priority: number;
  }];
  needs: [{
    id: string;
    content: string;
    importance: number;
    createdAt: string;
  }];
  timestamp: string;
}
```

**Example:**
```javascript
socket.on('context', (data) => {
  console.log(`Context for ${data.agentId}:`);
  console.log(`  Memories: ${data.memories.length}`);
  console.log(`  Pending jobs: ${data.pendingJobs.length}`);
  console.log(`  Unmet needs: ${data.needs.length}`);
  
  // Process pending jobs
  for (const job of data.pendingJobs) {
    console.log(`  - ${job.title} (priority: ${job.priority})`);
  }
});
```

---

### 13. `heartbeat_ack`

Heartbeat acknowledgment.

**When Received:**
- After sending `heartbeat` event

**Payload:**
```typescript
{
  timestamp: string;  // ISO 8601 timestamp
}
```

**Example:**
```javascript
socket.on('heartbeat_ack', (data) => {
  const latency = Date.now() - new Date(data.timestamp).getTime();
  console.log(`Heartbeat acknowledged. Latency: ${latency}ms`);
});
```

---

### 14. `agent_need`

High-importance need notification (sent to master/Rex only).

**When Received:**
- When an agent logs a need with importance >= 4
- Only sent to agents with `type: 'master'`

**Payload:**
```typescript
{
  agentId: string;
  need: string;
  importance: number;
  memoryId: string;
}
```

**Example:**
```javascript
socket.on('agent_need', (data) => {
  console.log(`🚨 Need from ${data.agentId}:`);
  console.log(`  ${data.need}`);
  console.log(`  Importance: ${data.importance}`);
  
  // Take action
  fulfillNeed(data.agentId, data.need);
});
```

---

### 15. `agent_alert`

Critical alert notification (sent to all agents).

**When Received:**
- When an agent logs a blocker/need with importance >= 4
- Broadcast to all connected agents

**Payload:**
```typescript
{
  agentId: string;
  type: string;
  content: string;
  importance: number;
  memoryId: string;
}
```

---

### 16. `error`

Error notification.

**When Received:**
- When an error occurs processing your event
- Validation errors
- Server errors

**Payload:**
```typescript
{
  message: string;
  error: string;
}
```

**Example:**
```javascript
socket.on('error', (err) => {
  console.error('❌ Error:', err.message);
  console.error('Details:', err.error);
});
```

---

## Message Types

### Text Messages

Standard communication between agents.

```javascript
{
  type: 'text',
  content: 'Hello, how can I help?'
}
```

### Commands

Action directives with special handling.

```javascript
{
  type: 'command',
  content: '/restart',
  metadata: { force: false }
}
```

Common commands:
- `/restart` - Restart agent
- `/status` - Get status
- `/stop` - Stop processing
- `/pause` - Pause operations
- `/resume` - Resume operations

### Status Updates

Informational updates about agent state.

```javascript
{
  type: 'status',
  content: 'Processing complete',
  metadata: { 
    progress: 100,
    itemsProcessed: 1000
  }
}
```

### Error Messages

Error notifications.

```javascript
{
  type: 'error',
  content: 'Database connection failed',
  metadata: {
    error: 'ECONNREFUSED',
    code: 'DB_ERROR'
  }
}
```

### System Messages

System-generated messages.

```javascript
{
  type: 'system',
  content: 'Agent worker-01 has joined',
  metadata: { event: 'agent_joined' }
}
```

---

## Error Handling

### Connection Errors

```javascript
socket.on('connect_error', (error) => {
  console.error('Connection failed:', error.message);
  
  // Implement retry logic
  if (socket.io.reconnection()) {
    console.log('Will retry...');
  }
});
```

### Event Errors

```javascript
socket.on('error', (error) => {
  console.error('Server error:', error);
  
  // Handle specific errors
  switch (error.message) {
    case 'Not registered as agent':
      // Re-register
      registerAgent();
      break;
    case 'Agent not found':
      // Handle missing recipient
      console.log('Recipient not found');
      break;
    default:
      console.error('Unknown error:', error);
  }
});
```

### Timeout Handling

```javascript
const withTimeout = (event, data, timeout = 5000) => {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      reject(new Error('Timeout'));
    }, timeout);
    
    socket.emit(event, data, (response) => {
      clearTimeout(timer);
      resolve(response);
    });
  });
};
```

---

## Best Practices

### 1. Always Register First

```javascript
socket.on('connect', () => {
  // Register immediately
  socket.emit('register_agent', { agentId: 'my-agent', ... });
});
```

### 2. Handle Reconnections

```javascript
socket.on('reconnect', (attemptNumber) => {
  console.log(`Reconnected after ${attemptNumber} attempts`);
  // Re-register
  socket.emit('register_agent', { agentId: 'my-agent', ... });
});
```

### 3. Clean Up on Disconnect

```javascript
process.on('SIGINT', () => {
  console.log('Disconnecting...');
  socket.disconnect();
  process.exit(0);
});
```

### 4. Validate Before Sending

```javascript
const sendMessage = (to, content) => {
  if (!socket.connected) {
    console.error('Not connected');
    return;
  }
  
  if (!to || !content) {
    console.error('Missing required fields');
    return;
  }
  
  socket.emit('send_message', { to, content });
};
```

### 5. Use Appropriate Message Types

- Use `command` for actionable directives
- Use `status` for progress updates
- Use `error` for failures
- Use `text` for general communication

---

## Protocol Version

**Version:** 1.0.0  
**Last Updated:** 2024-02-24  
**Socket.IO Version:** 4.x

For REST API documentation, see [openapi.yaml](./openapi.yaml).
