require('dotenv').config();

const express = require('express');
const http = require('http');
const cors = require('cors');
const helmet = require('helmet');
const rateLimit = require('express-rate-limit');

const config = require('./src/config/config');
const { requestLogger, errorHandler } = require('./src/middleware/logger');
const WebSocketServer = require('./src/websocket/server');
const { createTables } = require('./src/models');

// Import routes
const agentRoutes = require('./src/routes/agents');
const messageRoutes = require('./src/routes/messages');

async function startServer() {
  const app = express();
  const server = http.createServer(app);
  
  // Initialize WebSocket server
  const wsServer = new WebSocketServer(server);
  global.wsServer = wsServer; // Make available globally for routes
  
  // Security middleware
  app.use(helmet());
  app.use(cors());
  
  // Rate limiting
  const limiter = rateLimit({
    windowMs: 15 * 60 * 1000,
    max: 100,
    message: { error: 'Too many requests, please try again later' }
  });
  app.use(limiter);
  
  // Body parsing
  app.use(express.json({ limit: '10mb' }));
  app.use(express.urlencoded({ extended: true }));
  
  // Request logging
  app.use(requestLogger);
  
  // Health check
  app.get('/health', (req, res) => {
    res.json({
      status: 'ok',
      service: 'masterclaw-chat',
      timestamp: new Date().toISOString(),
      version: '1.0.0',
      connectedAgents: wsServer.getConnectedAgents().length
    });
  });
  
  // API routes
  app.use('/api/agents', agentRoutes);
  app.use('/api/messages', messageRoutes);
  
  // Stats endpoint
  app.get('/api/stats', async (req, res) => {
    try {
      const { Agent, Message, AgentJob } = require('./src/models');
      
      const [agents, pendingJobs] = await Promise.all([
        Agent.findAll(),
        AgentJob.getPendingJobs()
      ]);
      
      res.json({
        agents: {
          total: agents.length,
          online: agents.filter(a => a.status === 'online').length,
          offline: agents.filter(a => a.status === 'offline').length,
          busy: agents.filter(a => a.status === 'busy').length
        },
        jobs: {
          pending: pendingJobs.filter(j => j.status === 'pending').length,
          inProgress: pendingJobs.filter(j => j.status === 'in_progress').length
        },
        connectedNow: wsServer.getConnectedAgents()
      });
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  });
  
  // Broadcast endpoint (for admin use)
  app.post('/api/broadcast', (req, res) => {
    const { message, type = 'announcement' } = req.body;
    
    wsServer.broadcastToAll('broadcast', {
      type,
      message,
      timestamp: new Date().toISOString()
    });
    
    res.json({ success: true, message: 'Broadcast sent' });
  });
  
  // 404 handler
  app.use((req, res) => {
    res.status(404).json({ error: 'Endpoint not found' });
  });
  
  // Error handler
  app.use(errorHandler);
  
  // Initialize database
  try {
    await createTables();
    console.log('✅ Database initialized');
  } catch (error) {
    console.error('❌ Database initialization failed:', error);
    process.exit(1);
  }
  
  // Start server
  const PORT = config.port;
  server.listen(PORT, () => {
    console.log(`🚀 MasterClaw Chat Server running on port ${PORT}`);
    console.log(`📊 Environment: ${config.env}`);
    console.log(`🔌 WebSocket endpoint: ws://localhost:${PORT}`);
    console.log('');
    console.log('📚 API Endpoints:');
    console.log(`  GET  /health         - Health check`);
    console.log(`  GET  /api/agents     - List agents`);
    console.log(`  GET  /api/stats      - Server stats`);
    console.log('');
    console.log('🔌 WebSocket Events:');
    console.log('  register_agent       - Register as agent');
    console.log('  send_message         - Send message');
    console.log('  log_memory           - Log thought/memory');
    console.log('  create_job           - Create job/task');
  });
  
  return server;
}

// Handle uncaught errors
process.on('unhandledRejection', (err) => {
  console.error('Unhandled rejection:', err);
});

process.on('uncaughtException', (err) => {
  console.error('Uncaught exception:', err);
  process.exit(1);
});

// Start if not in test mode
if (process.env.NODE_ENV !== 'test') {
  startServer().catch(err => {
    console.error('Failed to start server:', err);
    process.exit(1);
  });
}

module.exports = { startServer };