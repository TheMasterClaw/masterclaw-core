const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const cors = require('cors');
const path = require('path');
const { v4: uuidv4 } = require('uuid');
require('dotenv').config();

const app = express();
const server = http.createServer(app);
const io = new Server(server, {
  cors: {
    origin: "*",
    methods: ["GET", "POST"]
  }
});

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, '../../frontend/dist')));

// ============================================
// AGENT REGISTRY - Core System
// ============================================
class AgentRegistry {
  constructor() {
    this.agents = new Map();
    this.rex = { id: 'rex', name: 'Rex Deus', role: 'master', socketId: null };
    this.initializeDefaultAgents();
  }

  initializeDefaultAgents() {
    const defaultAgents = [
      { id: 'agent-research', name: 'Research Agent', role: 'research', status: 'idle', capabilities: ['web_search', 'data_analysis', 'trends'] },
      { id: 'agent-coding', name: 'Coding Agent', role: 'coding', status: 'idle', capabilities: ['code_gen', 'debugging', 'architecture'] },
      { id: 'agent-devops', name: 'DevOps Agent', role: 'devops', status: 'idle', capabilities: ['cicd', 'cloud', 'monitoring'] },
      { id: 'agent-security', name: 'Security Agent', role: 'security', status: 'idle', capabilities: ['vuln_scan', 'compliance', 'alerts'] },
      { id: 'agent-qa', name: 'QA Agent', role: 'qa', status: 'idle', capabilities: ['testing', 'bug_tracking', 'coverage'] },
      { id: 'agent-content', name: 'Content Agent', role: 'content', status: 'idle', capabilities: ['writing', 'editing', 'seo'] },
      { id: 'agent-orchestrator', name: 'Orchestrator Agent', role: 'orchestrator', status: 'idle', capabilities: ['coordination', 'routing', 'scheduling'] }
    ];

    defaultAgents.forEach(agent => {
      this.agents.set(agent.id, { ...agent, socketId: null, lastSeen: null });
    });
  }

  getAllAgents() {
    return Array.from(this.agents.values()).map(a => ({
      id: a.id,
      name: a.name,
      role: a.role,
      status: a.status,
      capabilities: a.capabilities,
      online: !!a.socketId
    }));
  }

  getAgent(id) {
    return this.agents.get(id);
  }

  registerAgentSocket(agentId, socketId) {
    const agent = this.agents.get(agentId);
    if (agent) {
      agent.socketId = socketId;
      agent.status = 'online';
      agent.lastSeen = new Date().toISOString();
      return true;
    }
    return false;
  }

  unregisterSocket(socketId) {
    for (const [id, agent] of this.agents) {
      if (agent.socketId === socketId) {
        agent.socketId = null;
        agent.status = 'offline';
        return id;
      }
    }
    if (this.rex.socketId === socketId) {
      this.rex.socketId = null;
      return 'rex';
    }
    return null;
  }

  setRexSocket(socketId) {
    this.rex.socketId = socketId;
  }
}

// ============================================
// AGENT MEMORY SYSTEM
// ============================================
class AgentMemory {
  constructor() {
    this.memories = new Map(); // agentId -> { thoughts: [], jobs: [], needs: [] }
    this.conversations = new Map(); // conversationId -> messages[]
  }

  initializeAgentMemory(agentId) {
    if (!this.memories.has(agentId)) {
      this.memories.set(agentId, {
        thoughts: [],
        jobs: [],
        needs: [],
        lastUpdated: new Date().toISOString()
      });
    }
  }

  logThought(agentId, thought) {
    this.initializeAgentMemory(agentId);
    const memory = this.memories.get(agentId);
    memory.thoughts.push({
      id: uuidv4(),
      content: thought,
      timestamp: new Date().toISOString()
    });
    // Keep only last 100 thoughts
    if (memory.thoughts.length > 100) memory.thoughts.shift();
    memory.lastUpdated = new Date().toISOString();
  }

  logJob(agentId, job) {
    this.initializeAgentMemory(agentId);
    const memory = this.memories.get(agentId);
    memory.jobs.push({
      id: uuidv4(),
      ...job,
      timestamp: new Date().toISOString(),
      status: job.status || 'pending'
    });
    memory.lastUpdated = new Date().toISOString();
  }

  updateJobStatus(agentId, jobId, status) {
    const memory = this.memories.get(agentId);
    if (memory) {
      const job = memory.jobs.find(j => j.id === jobId);
      if (job) {
        job.status = status;
        job.updatedAt = new Date().toISOString();
      }
    }
  }

  logNeed(agentId, need) {
    this.initializeAgentMemory(agentId);
    const memory = this.memories.get(agentId);
    memory.needs.push({
      id: uuidv4(),
      content: need,
      timestamp: new Date().toISOString(),
      resolved: false
    });
    memory.lastUpdated = new Date().toISOString();
  }

  resolveNeed(agentId, needId) {
    const memory = this.memories.get(agentId);
    if (memory) {
      const need = memory.needs.find(n => n.id === needId);
      if (need) need.resolved = true;
    }
  }

  getMemory(agentId) {
    this.initializeAgentMemory(agentId);
    return this.memories.get(agentId);
  }

  storeMessage(conversationId, message) {
    if (!this.conversations.has(conversationId)) {
      this.conversations.set(conversationId, []);
    }
    const convo = this.conversations.get(conversationId);
    convo.push({
      id: uuidv4(),
      ...message,
      timestamp: new Date().toISOString()
    });
    // Keep last 1000 messages per conversation
    if (convo.length > 1000) convo.shift();
  }

  getConversation(conversationId) {
    return this.conversations.get(conversationId) || [];
  }
}

// ============================================
// MESSAGE ROUTER
// ============================================
class MessageRouter {
  constructor(agentRegistry, agentMemory, io) {
    this.registry = agentRegistry;
    this.memory = agentMemory;
    this.io = io;
  }

  routeMessage(from, to, content, metadata = {}) {
    const message = {
      id: uuidv4(),
      from,
      to,
      content,
      metadata,
      timestamp: new Date().toISOString()
    };

    // Store in conversation history
    const conversationId = [from, to].sort().join('-');
    this.memory.storeMessage(conversationId, message);

    // Log in sender's memory
    this.memory.logThought(from, `Sent message to ${to}: ${content.substring(0, 100)}...`);

    // Route to recipient if online
    const recipient = this.registry.getAgent(to);
    if (recipient && recipient.socketId) {
      this.io.to(recipient.socketId).emit('message', message);
      console.log(`[ROUTER] Message routed: ${from} -> ${to}`);
    } else if (to === 'rex') {
      // Route to Rex
      if (this.registry.rex.socketId) {
        this.io.to(this.registry.rex.socketId).emit('message', message);
        console.log(`[ROUTER] Message routed: ${from} -> Rex`);
      }
    } else {
      console.log(`[ROUTER] Recipient ${to} offline, message stored`);
    }

    // Broadcast to orchestrator for monitoring
    const orchestrator = this.registry.getAgent('agent-orchestrator');
    if (orchestrator && orchestrator.socketId) {
      this.io.to(orchestrator.socketId).emit('routing-log', message);
    }

    return message;
  }

  broadcastToAll(from, content) {
    const agents = this.registry.getAllAgents().filter(a => a.online);
    agents.forEach(agent => {
      this.routeMessage(from, agent.id, content, { broadcast: true });
    });
  }
}

// ============================================
// INITIALIZE SYSTEMS
// ============================================
const registry = new AgentRegistry();
const memory = new AgentMemory();
const router = new MessageRouter(registry, memory, io);

// ============================================
// SOCKET.IO CONNECTIONS
// ============================================
io.on('connection', (socket) => {
  console.log(`[SOCKET] Client connected: ${socket.id}`);

  // Register as Rex
  socket.on('register-rex', () => {
    registry.setRexSocket(socket.id);
    socket.join('rex');
    console.log(`[SOCKET] Rex registered: ${socket.id}`);
    socket.emit('registered', { role: 'rex', agents: registry.getAllAgents() });
  });

  // Register as Agent
  socket.on('register-agent', (agentId) => {
    const success = registry.registerAgentSocket(agentId, socket.id);
    if (success) {
      socket.join(agentId);
      memory.initializeAgentMemory(agentId);
      memory.logThought(agentId, 'Agent connected and registered');
      console.log(`[SOCKET] Agent registered: ${agentId} (${socket.id})`);
      socket.emit('registered', { role: 'agent', agentId, agents: registry.getAllAgents() });
      
      // Notify Rex of agent coming online
      if (registry.rex.socketId) {
        io.to(registry.rex.socketId).emit('agent-status', { agentId, status: 'online' });
      }
    } else {
      socket.emit('error', { message: 'Agent not found in registry' });
    }
  });

  // Direct message
  socket.on('send-message', (data) => {
    const { to, content, metadata } = data;
    const from = socket.rooms.has('rex') ? 'rex' : Array.from(socket.rooms)[1];
    
    if (from && to && content) {
      const message = router.routeMessage(from, to, content, metadata);
      socket.emit('message-sent', { messageId: message.id });
    }
  });

  // Broadcast message
  socket.on('broadcast', (data) => {
    const from = socket.rooms.has('rex') ? 'rex' : Array.from(socket.rooms)[1];
    router.broadcastToAll(from, data.content);
  });

  // Agent memory updates
  socket.on('log-thought', (data) => {
    const agentId = Array.from(socket.rooms)[1];
    if (agentId) {
      memory.logThought(agentId, data.thought);
    }
  });

  socket.on('log-job', (data) => {
    const agentId = Array.from(socket.rooms)[1];
    if (agentId) {
      memory.logJob(agentId, data);
    }
  });

  socket.on('log-need', (data) => {
    const agentId = Array.from(socket.rooms)[1];
    if (agentId) {
      memory.logNeed(agentId, data.need);
    }
  });

  // Request memory data
  socket.on('get-memory', (agentId, callback) => {
    const mem = memory.getMemory(agentId);
    callback(mem);
  });

  // Request conversation history
  socket.on('get-conversation', (data, callback) => {
    const { participant1, participant2 } = data;
    const conversationId = [participant1, participant2].sort().join('-');
    callback(memory.getConversation(conversationId));
  });

  // Disconnect
  socket.on('disconnect', () => {
    const agentId = registry.unregisterSocket(socket.id);
    if (agentId) {
      console.log(`[SOCKET] ${agentId} disconnected`);
      if (registry.rex.socketId) {
        io.to(registry.rex.socketId).emit('agent-status', { agentId, status: 'offline' });
      }
    }
  });
});

// ============================================
// REST API ENDPOINTS
// ============================================
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

app.get('/api/agents', (req, res) => {
  res.json(registry.getAllAgents());
});

app.get('/api/agents/:id/memory', (req, res) => {
  const mem = memory.getMemory(req.params.id);
  res.json(mem);
});

app.get('/api/conversation/:p1/:p2', (req, res) => {
  const conversationId = [req.params.p1, req.params.p2].sort().join('-');
  res.json(memory.getConversation(conversationId));
});

// Serve frontend
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, '../../frontend/dist/index.html'));
});

// ============================================
// START SERVER
// ============================================
const PORT = process.env.PORT || 3001;
server.listen(PORT, () => {
  console.log(`
╔════════════════════════════════════════════════════════════╗
║         MASTERCLAW CHAT INTERFACE - ONLINE                 ║
║                                                            ║
║  WebSocket Server: ws://localhost:${PORT}                ║
║  REST API: http://localhost:${PORT}/api                   ║
║                                                            ║
║  Registered Agents: ${registry.getAllAgents().length}                                    ║
║                                                            ║
║  System Ready for Rex-to-Agent Communication               ║
╚════════════════════════════════════════════════════════════╝
  `);
});

module.exports = { app, server, io, registry, memory, router };
