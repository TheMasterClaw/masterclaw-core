const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const cors = require('cors');
require('dotenv').config();

const app = express();
const server = http.createServer(app);
const io = new Server(server, {
  cors: {
    origin: process.env.FRONTEND_URL || "http://localhost:3000",
    methods: ["GET", "POST"]
  }
});

// Middleware
app.use(cors());
app.use(express.json());

// In-memory storage (replace with PostgreSQL in production)
const agents = new Map();
const messages = [];
const agentMemory = new Map(); // jobs, desires, blockers

// Agent class
class Agent {
  constructor(id, name, role) {
    this.id = id;
    this.name = name;
    this.role = role;
    this.status = 'online';
    this.socketId = null;
    this.lastSeen = new Date();
    this.jobs = [];
    this.desires = [];
    this.blockers = [];
  }
}

// API Routes
app.get('/api/agents', (req, res) => {
  const agentList = Array.from(agents.values()).map(a => ({
    id: a.id,
    name: a.name,
    role: a.role,
    status: a.status,
    lastSeen: a.lastSeen
  }));
  res.json(agentList);
});

app.get('/api/agents/:id', (req, res) => {
  const agent = agents.get(req.params.id);
  if (!agent) return res.status(404).json({ error: 'Agent not found' });
  res.json({
    id: agent.id,
    name: agent.name,
    role: agent.role,
    status: agent.status,
    lastSeen: agent.lastSeen,
    jobs: agent.jobs,
    desires: agent.desires,
    blockers: agent.blockers
  });
});

app.get('/api/agents/:id/messages', (req, res) => {
  const agentMessages = messages.filter(
    m => m.from === req.params.id || m.to === req.params.id
  );
  res.json(agentMessages);
});

app.post('/api/messages', (req, res) => {
  const { from, to, content, type = 'text' } = req.body;
  const message = {
    id: Date.now().toString(),
    from,
    to,
    content,
    type,
    timestamp: new Date().toISOString(),
    read: false
  };
  messages.push(message);
  
  // Emit to recipient if online
  const recipientAgent = agents.get(to);
  if (recipientAgent && recipientAgent.socketId) {
    io.to(recipientAgent.socketId).emit('message', message);
  }
  
  res.json(message);
});

// Agent memory endpoints
app.post('/api/agents/:id/jobs', (req, res) => {
  const agent = agents.get(req.params.id);
  if (!agent) return res.status(404).json({ error: 'Agent not found' });
  
  const job = {
    id: Date.now().toString(),
    agentId: req.params.id,
    title: req.body.title,
    description: req.body.description,
    status: 'pending',
    startedAt: new Date().toISOString(),
    completedAt: null,
    result: null
  };
  agent.jobs.push(job);
  
  // Notify subscribers
  io.emit('memory:updated', { agentId: req.params.id, type: 'job', data: job });
  res.json(job);
});

app.post('/api/agents/:id/desires', (req, res) => {
  const agent = agents.get(req.params.id);
  if (!agent) return res.status(404).json({ error: 'Agent not found' });
  
  const desire = {
    id: Date.now().toString(),
    agentId: req.params.id,
    description: req.body.description,
    priority: req.body.priority || 'medium',
    createdAt: new Date().toISOString(),
    fulfilledAt: null
  };
  agent.desires.push(desire);
  io.emit('memory:updated', { agentId: req.params.id, type: 'desire', data: desire });
  res.json(desire);
});

app.post('/api/agents/:id/blockers', (req, res) => {
  const agent = agents.get(req.params.id);
  if (!agent) return res.status(404).json({ error: 'Agent not found' });
  
  const blocker = {
    id: Date.now().toString(),
    agentId: req.params.id,
    description: req.body.description,
    severity: req.body.severity || 'medium',
    createdAt: new Date().toISOString(),
    resolvedAt: null
  };
  agent.blockers.push(blocker);
  io.emit('memory:updated', { agentId: req.params.id, type: 'blocker', data: blocker });
  res.json(blocker);
});

// WebSocket handling
io.on('connection', (socket) => {
  console.log('Client connected:', socket.id);
  
  // Agent registration
  socket.on('register', (data) => {
    const { agentId, name, role } = data;
    let agent = agents.get(agentId);
    
    if (!agent) {
      agent = new Agent(agentId, name, role);
      agents.set(agentId, agent);
    }
    
    agent.socketId = socket.id;
    agent.status = 'online';
    agent.lastSeen = new Date();
    
    socket.agentId = agentId;
    socket.join(agentId);
    
    console.log(`Agent registered: ${name} (${agentId})`);
    io.emit('agent:joined', { agentId, name, role, status: 'online' });
  });
  
  // Handle messages
  socket.on('message', (data) => {
    const { to, content, type = 'text' } = data;
    const from = socket.agentId;
    
    if (!from) {
      socket.emit('error', { message: 'Not registered' });
      return;
    }
    
    const message = {
      id: Date.now().toString(),
      from,
      to,
      content,
      type,
      timestamp: new Date().toISOString(),
      read: false
    };
    messages.push(message);
    
    // Send to recipient
    const recipientAgent = agents.get(to);
    if (recipientAgent && recipientAgent.socketId) {
      io.to(recipientAgent.socketId).emit('message', message);
    }
    
    // Confirm to sender
    socket.emit('message:sent', { messageId: message.id });
  });
  
  // Status updates
  socket.on('status', (data) => {
    const agent = agents.get(socket.agentId);
    if (agent) {
      agent.status = data.status;
      io.emit('agent:status', { agentId: socket.agentId, status: data.status });
    }
  });
  
  // Typing indicators
  socket.on('typing', (data) => {
    const { to } = data;
    const recipientAgent = agents.get(to);
    if (recipientAgent && recipientAgent.socketId) {
      io.to(recipientAgent.socketId).emit('agent:typing', { 
        agentId: socket.agentId 
      });
    }
  });
  
  // Disconnect handling
  socket.on('disconnect', () => {
    console.log('Client disconnected:', socket.id);
    if (socket.agentId) {
      const agent = agents.get(socket.agentId);
      if (agent) {
        agent.status = 'offline';
        agent.socketId = null;
        io.emit('agent:status', { agentId: socket.agentId, status: 'offline' });
      }
    }
  });
});

// Health check
app.get('/health', (req, res) => {
  res.json({ 
    status: 'ok', 
    agents: agents.size,
    messages: messages.length,
    uptime: process.uptime()
  });
});

const PORT = process.env.PORT || 3001;
server.listen(PORT, () => {
  console.log(`🚀 MasterClaw Interface Server running on port ${PORT}`);
  console.log(`📡 WebSocket ready for connections`);
});
