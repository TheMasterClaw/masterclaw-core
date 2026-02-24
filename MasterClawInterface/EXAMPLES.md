# MasterClaw Chat Interface - Usage Examples

Complete code examples for integrating with the MasterClaw Chat Interface.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Agent SDK Usage](#agent-sdk-usage)
3. [WebSocket Protocol](#websocket-protocol)
4. [REST API Examples](#rest-api-examples)
5. [Rex Integration](#rex-integration)
6. [React Chat UI](#react-chat-ui)
7. [Advanced Patterns](#advanced-patterns)

---

## Quick Start

### 1. Start the Server

```bash
# Using Docker (recommended)
cd docker
docker-compose up -d

# Or manually
cd backend
npm install
npm run dev
```

### 2. Connect Your First Agent

```javascript
const { MasterClawAgent } = require('@masterclaw/agent-client');

const agent = new MasterClawAgent({
  agentId: 'my-first-agent',
  name: 'Demo Agent',
  type: 'worker',
  serverUrl: 'http://localhost:3001'
});

await agent.connect();
console.log('Connected to MasterClaw!');
```

---

## Agent SDK Usage

### Basic Agent Setup

```javascript
const { MasterClawAgent } = require('@masterclaw/agent-client');

class MyAgent extends MasterClawAgent {
  constructor(config) {
    super(config);
    this.setupHandlers();
  }

  setupHandlers() {
    // Handle incoming messages
    this.on('message', async (msg) => {
      console.log(`📨 From ${msg.from}: ${msg.content}`);
      
      // Auto-reply to Rex
      if (msg.from === 'rex') {
        await this.sendMessage(msg.from, `Received: ${msg.content}`);
      }
    });

    // Handle new jobs
    this.on('newJob', async (job) => {
      console.log(`📝 New job: ${job.title}`);
      await this.processJob(job);
    });

    // Handle disconnections
    this.on('disconnect', () => {
      console.log('⚠️ Disconnected from MasterClaw');
    });

    // Handle reconnections
    this.on('reconnect', () => {
      console.log('✅ Reconnected to MasterClaw');
    });
  }

  async processJob(job) {
    await this.updateJobStatus(job.jobId, 'in_progress');
    
    // Do work...
    await this.logThought(`Processing job: ${job.title}`);
    
    // Complete job
    await this.updateJobStatus(job.jobId, 'completed', {
      result: 'success',
      output: 'Job completed successfully'
    });
  }
}

// Create and connect
const agent = new MyAgent({
  agentId: 'data-processor',
  name: 'Data Processor',
  type: 'worker',
  capabilities: ['data-processing', 'analysis'],
  serverUrl: 'http://localhost:3001'
});

await agent.connect();
```

### Logging Memories

```javascript
// Log a thought (internal reasoning)
await agent.logThought(
  'Analyzing the data structure...',
  2  // importance: 1-5
);

// Log a need (will notify master if importance >= 4)
await agent.logNeed(
  'Need access to production database',
  4  // high importance - master will be notified
);

// Log an observation
await agent.logObservation(
  'CPU usage is at 85%',
  { metric: 'cpu', value: 85 },
  3
);

// Log a decision
await agent.logDecision(
  'Chose PostgreSQL over MongoDB for ACID compliance',
  { options: ['postgresql', 'mongodb'], selected: 'postgresql' },
  2
);
```

### Creating and Managing Jobs

```javascript
// Create a job for yourself
const myJob = await agent.createJob({
  title: 'Process daily reports',
  description: 'Generate and email daily analytics reports',
  priority: 3
});

// Create a job for another agent
const delegatedJob = await agent.createJob({
  title: 'Review PR #123',
  description: 'Check code quality and test coverage',
  priority: 4,
  assignTo: 'code-reviewer-agent'
});

// Update job status
await agent.updateJobStatus(myJob.jobId, 'in_progress');
await agent.updateJobStatus(myJob.jobId, 'completed', {
  success: true,
  reportsGenerated: 5,
  errors: 0
});
```

### Messaging Patterns

```javascript
// Send direct message
await agent.sendMessage('rex', 'Task completed!');

// Send command
await agent.sendMessage('worker-beta', '/restart', 'command');

// Send with metadata
await agent.sendMessage('analytics-agent', 'Process this data', 'text', {
  datasetId: 'ds-123',
  priority: 'high'
});

// Message Rex specifically
await agent.messageRex('I need help with database connection');

// Broadcast to all agents
await agent.broadcast('System maintenance in 5 minutes');
```

---

## WebSocket Protocol

### Raw WebSocket Usage (without SDK)

```javascript
const io = require('socket.io-client');

const socket = io('http://localhost:3001');

socket.on('connect', () => {
  console.log('Connected');
  
  // Register as agent
  socket.emit('register_agent', {
    agentId: 'raw-agent',
    name: 'Raw Socket Agent',
    type: 'worker',
    capabilities: ['testing']
  });
});

// Handle registration confirmation
socket.on('registered', (data) => {
  console.log('Registered:', data.agent);
});

// Handle incoming messages
socket.on('message', (data) => {
  console.log(`From ${data.from}: ${data.content}`);
  
  // Reply
  socket.emit('send_message', {
    to: data.from,
    content: 'Got it!',
    type: 'text'
  });
});

// Handle new jobs
socket.on('new_job', (job) => {
  console.log('New job:', job);
});

// Handle typing indicators
socket.on('typing', (data) => {
  console.log(`${data.from} is typing...`);
});

// Handle agent status changes
socket.on('agent_status', (data) => {
  console.log(`${data.agentId} is now ${data.status}`);
});

// Handle errors
socket.on('error', (err) => {
  console.error('Error:', err);
});

// Send heartbeat every 30 seconds
setInterval(() => {
  socket.emit('heartbeat', { timestamp: Date.now() });
}, 30000);

socket.on('heartbeat_ack', (data) => {
  console.log('Heartbeat acknowledged:', data.timestamp);
});
```

### WebSocket Event Reference

#### Client → Server Events

| Event | Data | Description |
|-------|------|-------------|
| `register_agent` | `{ agentId, name, type, capabilities }` | Register as an agent |
| `send_message` | `{ to, content, type, metadata }` | Send message to agent |
| `typing` | `{ to, isTyping }` | Typing indicator |
| `heartbeat` | `{ timestamp }` | Keep connection alive |
| `log_memory` | `{ memoryType, content, context, importance }` | Log thought/need |
| `create_job` | `{ title, description, priority, assignTo }` | Create job |
| `update_job` | `{ jobId, status, result }` | Update job status |
| `get_context` | `{}` | Get agent context |

#### Server → Client Events

| Event | Data | Description |
|-------|------|-------------|
| `registered` | `{ success, agent }` | Registration confirmed |
| `message` | `{ id, messageId, from, to, content, type, timestamp }` | Incoming message |
| `message_sent` | `{ success, messageId, delivered }` | Message sent confirmation |
| `typing` | `{ from, isTyping }` | Typing indicator from other agent |
| `agent_status` | `{ agentId, status, timestamp }` | Agent status change |
| `unread_messages` | `[{ ...message }]` | Pending messages on connect |
| `memory_logged` | `{ success, memoryId }` | Memory logged confirmation |
| `new_job` | `{ jobId, title, description, priority }` | New job assigned |
| `job_created` | `{ success, job }` | Job created confirmation |
| `job_updated` | `{ success, job }` | Job updated confirmation |
| `context` | `{ agentId, memories, pendingJobs, needs }` | Agent context |
| `heartbeat_ack` | `{ timestamp }` | Heartbeat response |
| `error` | `{ message, error }` | Error notification |

---

## REST API Examples

### Using curl

```bash
# Health check
curl http://localhost:3001/health

# List all agents
curl http://localhost:3001/api/agents

# Register new agent
curl -X POST http://localhost:3001/api/agents \
  -H "Content-Type: application/json" \
  -d '{
    "agentId": "curl-agent",
    "name": "CURL Test Agent",
    "type": "worker",
    "capabilities": ["testing"]
  }'

# Get agent details
curl http://localhost:3001/api/agents/curl-agent

# Get agent memories
curl http://localhost:3001/api/agents/curl-agent/memory

# Get agent jobs
curl http://localhost:3001/api/agents/curl-agent/jobs

# Create a job
curl -X POST http://localhost:3001/api/agents/curl-agent/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test Job",
    "description": "Job created via curl",
    "priority": 3
  }'

# Get conversation between two agents
curl http://localhost:3001/api/messages/conversation/rex/curl-agent

# Get unread messages
curl http://localhost:3001/api/messages/agent/curl-agent/unread
```

### Using JavaScript/Node.js

```javascript
const axios = require('axios');

const API_URL = 'http://localhost:3001';

class MasterClawAPI {
  constructor(baseURL = API_URL) {
    this.client = axios.create({ baseURL });
  }

  // Agents
  async listAgents(filters = {}) {
    const { data } = await this.client.get('/api/agents', { params: filters });
    return data.agents;
  }

  async getAgent(agentId) {
    const { data } = await this.client.get(`/api/agents/${agentId}`);
    return data.agent;
  }

  async createAgent(agentData) {
    const { data } = await this.client.post('/api/agents', agentData);
    return data.agent;
  }

  async updateAgent(agentId, updates) {
    const { data } = await this.client.put(`/api/agents/${agentId}`, updates);
    return data.agent;
  }

  async deleteAgent(agentId) {
    await this.client.delete(`/api/agents/${agentId}`);
    return true;
  }

  // Memories
  async getMemories(agentId, options = {}) {
    const { data } = await this.client.get(
      `/api/agents/${agentId}/memory`,
      { params: options }
    );
    return data.memories;
  }

  async logMemory(agentId, memoryType, content, options = {}) {
    const { data } = await this.client.post(
      `/api/agents/${agentId}/memory`,
      { memoryType, content, ...options }
    );
    return data.memory;
  }

  // Jobs
  async getJobs(agentId, options = {}) {
    const { data } = await this.client.get(
      `/api/agents/${agentId}/jobs`,
      { params: options }
    );
    return data.jobs;
  }

  async createJob(agentId, jobData) {
    const { data } = await this.client.post(
      `/api/agents/${agentId}/jobs`,
      jobData
    );
    return data.job;
  }

  async updateJob(agentId, jobId, status, result) {
    const { data } = await this.client.put(
      `/api/agents/${agentId}/jobs/${jobId}`,
      { status, result }
    );
    return data.job;
  }

  // Messages
  async getConversation(agent1, agent2, options = {}) {
    const { data } = await this.client.get(
      `/api/messages/conversation/${agent1}/${agent2}`,
      { params: options }
    );
    return data.messages;
  }

  async getMessages(agentId, options = {}) {
    const { data } = await this.client.get(
      `/api/messages/agent/${agentId}`,
      { params: options }
    );
    return data.messages;
  }

  async sendMessage(messageData) {
    const { data } = await this.client.post('/api/messages', messageData);
    return data.message;
  }

  async getUnreadCount(agentId) {
    const { data } = await this.client.get(
      `/api/messages/agent/${agentId}/unread`
    );
    return data.unreadCount;
  }

  async markAsRead(messageId) {
    const { data } = await this.client.put(`/api/messages/${messageId}/read`);
    return data.message;
  }

  // Server
  async healthCheck() {
    const { data } = await this.client.get('/health');
    return data;
  }

  async getStats() {
    const { data } = await this.client.get('/api/stats');
    return data;
  }
}

// Usage
const api = new MasterClawAPI();

async function example() {
  // Create agent
  const agent = await api.createAgent({
    agentId: 'api-agent',
    name: 'API Test Agent',
    type: 'worker'
  });

  // Log a memory
  await api.logMemory('api-agent', 'thought', 'Testing the API', {
    importance: 2
  });

  // Get memories
  const memories = await api.getMemories('api-agent');
  console.log('Memories:', memories);
}

example().catch(console.error);
```

---

## Rex Integration

### Rex Agent Implementation

```javascript
const { MasterClawAgent } = require('@masterclaw/agent-client');

class RexAgent extends MasterClawAgent {
  constructor() {
    super({
      agentId: 'rex',
      name: 'Rex',
      type: 'master',
      capabilities: ['coordination', 'management', 'decision-making'],
      serverUrl: process.env.MASTERCLAW_URL || 'http://localhost:3001'
    });

    this.activeAgents = new Map();
    this.pendingNeeds = [];
    this.setupRexHandlers();
  }

  setupRexHandlers() {
    // Handle all messages
    this.on('message', async (msg) => {
      console.log(`🎯 [Rex] Message from ${msg.from}: ${msg.content}`);
      await this.handleIncomingMessage(msg);
    });

    // Handle agent alerts (high-importance needs)
    this.on('agent_alert', async (alert) => {
      console.log(`🚨 [Rex] Alert from ${alert.agentId}: ${alert.content}`);
      this.pendingNeeds.push(alert);
      await this.handleAgentAlert(alert);
    });

    // Handle agent needs
    this.on('agent_need', async (need) => {
      console.log(`💡 [Rex] Need from ${need.agentId}: ${need.need}`);
      await this.handleAgentNeed(need);
    });

    // Handle new agents coming online
    this.on('agent_status', async (status) => {
      console.log(`📡 [Rex] ${status.agentId} is ${status.status}`);
      
      if (status.status === 'online') {
        await this.onboardAgent(status.agentId);
      }
    });

    // Handle job completions
    this.on('job_status', async (job) => {
      console.log(`✅ [Rex] Job ${job.jobId} ${job.status} by ${job.completedBy}`);
      await this.handleJobCompletion(job);
    });
  }

  async handleIncomingMessage(msg) {
    // Parse commands
    if (msg.content.startsWith('/')) {
      await this.handleCommand(msg.from, msg.content);
      return;
    }

    // Natural language processing
    const response = await this.processNaturalLanguage(msg.content);
    await this.sendMessage(msg.from, response);
  }

  async handleCommand(fromAgent, command) {
    const parts = command.slice(1).split(' ');
    const cmd = parts[0];
    const args = parts.slice(1);

    switch (cmd) {
      case 'status':
        const stats = await this.getServerStats();
        await this.sendMessage(fromAgent, `📊 Server Status: ${JSON.stringify(stats, null, 2)}`);
        break;

      case 'agents':
        const agents = await this.getActiveAgents();
        await this.sendMessage(fromAgent, `👥 Active Agents: ${agents.join(', ')}`);
        break;

      case 'assign':
        const [jobTitle, ...targetAgentParts] = args;
        const targetAgent = targetAgentParts.join(' ');
        await this.createJob({
          title: jobTitle,
          priority: 3,
          assignTo: targetAgent
        });
        await this.sendMessage(fromAgent, `📋 Job "${jobTitle}" assigned to ${targetAgent}`);
        break;

      case 'broadcast':
        const message = args.join(' ');
        await this.broadcast(`[Rex] ${message}`);
        break;

      default:
        await this.sendMessage(fromAgent, `❓ Unknown command: ${cmd}`);
    }
  }

  async handleAgentAlert(alert) {
    // Immediate response to critical alerts
    if (alert.importance >= 4) {
      await this.sendMessage(
        alert.agentId,
        `🚨 I received your alert: "${alert.content}". Looking into it now.`
      );
      
      // Take action based on alert type
      if (alert.type === 'need') {
        await this.fulfillNeed(alert.agentId, alert.content);
      }
    }
  }

  async handleAgentNeed(need) {
    // Queue and prioritize needs
    this.pendingNeeds.push({
      agentId: need.agentId,
      need: need.need,
      importance: need.importance,
      timestamp: new Date()
    });

    // Sort by importance
    this.pendingNeeds.sort((a, b) => b.importance - a.importance);

    // Process highest priority need
    const topNeed = this.pendingNeeds[0];
    await this.fulfillNeed(topNeed.agentId, topNeed.need);
  }

  async fulfillNeed(agentId, need) {
    // Implement need fulfillment logic
    console.log(`[Rex] Fulfilling need for ${agentId}: ${need}`);
    
    // Example: If agent needs database access, grant it
    if (need.includes('database')) {
      await this.sendMessage(agentId, '🔑 Database credentials sent via secure channel');
    }
  }

  async onboardAgent(agentId) {
    await this.sendMessage(agentId, 
      `👋 Welcome, ${agentId}! I'm Rex, your coordinator. ` +
      `Type /help for available commands.`
    );
  }

  async getActiveAgents() {
    // Fetch from API
    const response = await fetch(`${this.serverUrl}/api/agents?status=online`);
    const data = await response.json();
    return data.agents.map(a => a.agentId);
  }

  async getServerStats() {
    const response = await fetch(`${this.serverUrl}/api/stats`);
    return await response.json();
  }

  async processNaturalLanguage(content) {
    // Simple response generation
    // In production, this would use an LLM
    const responses = [
      "I understand. Let me help with that.",
      "Processing your request...",
      "I'll coordinate with the appropriate agents.",
      "Acknowledged. Working on it now."
    ];
    return responses[Math.floor(Math.random() * responses.length)];
  }
}

// Start Rex
const rex = new RexAgent();
rex.connect().then(() => {
  console.log('🦖 Rex is online and ready to coordinate!');
});

module.exports = RexAgent;
```

---

## React Chat UI

### Custom Chat Component

```tsx
import React, { useState, useEffect, useRef } from 'react';
import { useSocket } from './hooks/useSocket';

interface Message {
  id: string;
  from: string;
  content: string;
  timestamp: string;
  type: string;
}

interface Agent {
  agentId: string;
  name: string;
  status: 'online' | 'offline' | 'busy' | 'away';
}

export const ChatInterface: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [selectedAgent, setSelectedAgent] = useState<string>('rex');
  const [agents, setAgents] = useState<Agent[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const { socket, isConnected, sendMessage } = useSocket({
    agentId: 'web-user',
    name: 'Web User',
    serverUrl: 'http://localhost:3001'
  });

  useEffect(() => {
    if (!socket) return;

    // Listen for messages
    socket.on('message', (msg: Message) => {
      setMessages(prev => [...prev, msg]);
    });

    // Listen for agent status changes
    socket.on('agent_status', (status: { agentId: string; status: string }) => {
      setAgents(prev => 
        prev.map(a => 
          a.agentId === status.agentId 
            ? { ...a, status: status.status as any }
            : a
        )
      );
    });

    // Fetch agents list
    fetch('http://localhost:3001/api/agents')
      .then(r => r.json())
      .then(data => setAgents(data.agents));

    return () => {
      socket.off('message');
      socket.off('agent_status');
    };
  }, [socket]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = () => {
    if (!inputValue.trim() || !isConnected) return;

    sendMessage(selectedAgent, inputValue);
    
    // Optimistically add to UI
    setMessages(prev => [...prev, {
      id: Date.now().toString(),
      from: 'web-user',
      content: inputValue,
      timestamp: new Date().toISOString(),
      type: 'text'
    }]);
    
    setInputValue('');
  };

  return (
    <div className="flex h-screen bg-gray-900 text-white">
      {/* Agent Sidebar */}
      <div className="w-64 bg-gray-800 border-r border-gray-700">
        <div className="p-4 border-b border-gray-700">
          <h2 className="font-bold">Agents</h2>
          <div className={`text-sm ${isConnected ? 'text-green-400' : 'text-red-400'}`}>
            {isConnected ? '🟢 Connected' : '🔴 Disconnected'}
          </div>
        </div>
        
        <div className="p-2">
          {agents.map(agent => (
            <button
              key={agent.agentId}
              onClick={() => setSelectedAgent(agent.agentId)}
              className={`w-full p-3 rounded text-left transition ${
                selectedAgent === agent.agentId
                  ? 'bg-blue-600'
                  : 'hover:bg-gray-700'
              }`}
            >
              <div className="flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full ${
                  agent.status === 'online' ? 'bg-green-400' :
                  agent.status === 'busy' ? 'bg-yellow-400' :
                  agent.status === 'away' ? 'bg-orange-400' :
                  'bg-gray-400'
                }`} />
                <span>{agent.name}</span>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="p-4 border-b border-gray-700 bg-gray-800">
          <h3 className="font-bold">Chat with {selectedAgent}</h3>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.map(msg => (
            <div
              key={msg.id}
              className={`flex ${
                msg.from === 'web-user' ? 'justify-end' : 'justify-start'
              }`}
            >
              <div className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                msg.from === 'web-user'
                  ? 'bg-blue-600'
                  : 'bg-gray-700'
              }`}>
                <div className="text-xs opacity-75 mb-1">{msg.from}</div>
                <div>{msg.content}</div>
                <div className="text-xs opacity-50 mt-1">
                  {new Date(msg.timestamp).toLocaleTimeString()}
                </div>
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="p-4 border-t border-gray-700 bg-gray-800">
          <div className="flex gap-2">
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSend()}
              placeholder="Type a message..."
              className="flex-1 px-4 py-2 bg-gray-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button
              onClick={handleSend}
              disabled={!isConnected}
              className="px-6 py-2 bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Send
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
```

---

## Advanced Patterns

### Agent Orchestration

```javascript
// Multi-agent workflow
class Orchestrator {
  constructor() {
    this.agents = new Map();
  }

  async createWorkflow(name, steps) {
    const workflowId = `wf-${Date.now()}`;
    
    for (const step of steps) {
      await this.assignStep(workflowId, step);
    }
    
    return workflowId;
  }

  async assignStep(workflowId, step) {
    const { agentType, task, dependencies = [] } = step;
    
    // Find available agent
    const agent = await this.findAgent(agentType);
    
    // Wait for dependencies
    if (dependencies.length > 0) {
      await this.waitForDependencies(workflowId, dependencies);
    }
    
    // Assign job
    await agent.createJob({
      title: task,
      priority: step.priority || 2,
      metadata: { workflowId, stepId: step.id }
    });
  }

  async findAgent(type) {
    // Query for available agents
    const response = await fetch(
      `http://localhost:3001/api/agents?type=${type}&status=online`
    );
    const { agents } = await response.json();
    
    if (agents.length === 0) {
      throw new Error(`No available agents of type: ${type}`);
    }
    
    // Return first available
    return agents[0];
  }
}
```

### Error Handling & Retry Logic

```javascript
class ResilientAgent extends MasterClawAgent {
  constructor(config) {
    super(config);
    this.retryAttempts = 3;
    this.retryDelay = 1000;
  }

  async sendWithRetry(to, content, attempt = 1) {
    try {
      await this.sendMessage(to, content);
    } catch (error) {
      if (attempt < this.retryAttempts) {
        console.log(`Retry ${attempt}/${this.retryAttempts}...`);
        await this.delay(this.retryDelay * attempt);
        return this.sendWithRetry(to, content, attempt + 1);
      }
      throw error;
    }
  }

  delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  async safeOperation(operation) {
    try {
      return await operation();
    } catch (error) {
      await this.logNeed(`Operation failed: ${error.message}`, 4);
      throw error;
    }
  }
}
```

### Metrics & Monitoring

```javascript
class MonitoredAgent extends MasterClawAgent {
  constructor(config) {
    super(config);
    this.metrics = {
      messagesSent: 0,
      messagesReceived: 0,
      jobsCompleted: 0,
      errors: 0,
      startTime: Date.now()
    };
  }

  async sendMessage(to, content, type = 'text', metadata = {}) {
    this.metrics.messagesSent++;
    return super.sendMessage(to, content, type, metadata);
  }

  onMessage(handler) {
    return super.on('message', (msg) => {
      this.metrics.messagesReceived++;
      handler(msg);
    });
  }

  async reportMetrics() {
    const uptime = Date.now() - this.metrics.startTime;
    
    await this.logObservation('Agent metrics report', {
      metrics: this.metrics,
      uptime,
      messagesPerMinute: (this.metrics.messagesReceived / (uptime / 60000)).toFixed(2)
    }, 2);
  }
}
```

---

## Next Steps

1. **Deploy your agents** using the Docker setup
2. **Customize Rex** with your specific coordination logic
3. **Build custom UIs** using the React components
4. **Monitor** agent health and performance
5. **Scale** with multiple agent instances

For more information, see:
- [API Documentation](./API.md)
- [OpenAPI Specification](./openapi.yaml)
- [Project Status](./PROJECT_STATUS.md)
