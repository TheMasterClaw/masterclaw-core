const { Server } = require('socket.io');
const config = require('../config/config');
const logger = require('../middleware/logger');
const { Agent, Message, AgentMemory, AgentJob } = require('../models');

// In-memory store for connected sockets
const connectedAgents = new Map(); // agentId -> socket
const socketToAgent = new Map();   // socketId -> agentId

class WebSocketServer {
  constructor(httpServer) {
    this.io = new Server(httpServer, {
      cors: {
        origin: '*', // Configure for production
        methods: ['GET', 'POST']
      },
      pingTimeout: 60000,
      pingInterval: 25000
    });
    
    this.setupHandlers();
    this.startHeartbeatCheck();
  }
  
  setupHandlers() {
    this.io.on('connection', (socket) => {
      logger.info(`Client connected: ${socket.id}`);
      
      // Register agent
      socket.on('register_agent', async (data) => {
        await this.handleRegisterAgent(socket, data);
      });
      
      // Send message
      socket.on('send_message', async (data) => {
        await this.handleSendMessage(socket, data);
      });
      
      // Typing indicator
      socket.on('typing', (data) => {
        this.handleTyping(socket, data);
      });
      
      // Heartbeat
      socket.on('heartbeat', async (data) => {
        await this.handleHeartbeat(socket, data);
      });
      
      // Log memory/thought
      socket.on('log_memory', async (data) => {
        await this.handleLogMemory(socket, data);
      });
      
      // Create job
      socket.on('create_job', async (data) => {
        await this.handleCreateJob(socket, data);
      });
      
      // Update job status
      socket.on('update_job', async (data) => {
        await this.handleUpdateJob(socket, data);
      });
      
      // Get agent context
      socket.on('get_context', async (data) => {
        await this.handleGetContext(socket, data);
      });
      
      // Disconnect
      socket.on('disconnect', () => {
        this.handleDisconnect(socket);
      });
    });
  }
  
  async handleRegisterAgent(socket, { agentId, name, type, capabilities }) {
    try {
      // Check if agent exists
      let agent = await Agent.findByAgentId(agentId);
      
      if (!agent) {
        // Create new agent
        agent = await Agent.create({
          agentId,
          name: name || agentId,
          type: type || 'subagent',
          capabilities: capabilities || []
        });
        logger.info(`New agent registered: ${agentId}`);
      } else {
        // Update existing agent
        await Agent.updateStatus(agentId, 'online', socket.id);
        logger.info(`Agent reconnected: ${agentId}`);
      }
      
      // Store socket mapping
      connectedAgents.set(agentId, socket);
      socketToAgent.set(socket.id, agentId);
      
      // Join agent to their room
      socket.join(`agent:${agentId}`);
      
      // Send confirmation
      socket.emit('registered', {
        success: true,
        agent: {
          id: agent.id,
          agentId: agent.agent_id,
          name: agent.name,
          type: agent.type,
          status: 'online'
        }
      });
      
      // Broadcast agent online status
      this.io.emit('agent_status', {
        agentId,
        status: 'online',
        timestamp: new Date().toISOString()
      });
      
      // Send any unread messages
      const unreadMessages = await Message.findForAgent(agentId, { unreadOnly: true, limit: 50 });
      if (unreadMessages.length > 0) {
        socket.emit('unread_messages', unreadMessages);
      }
      
    } catch (error) {
      logger.error('Error registering agent:', error);
      socket.emit('error', { message: 'Failed to register agent', error: error.message });
    }
  }
  
  async handleSendMessage(socket, { to, content, type = 'text', metadata = {} }) {
    try {
      const fromAgentId = socketToAgent.get(socket.id);
      
      if (!fromAgentId) {
        socket.emit('error', { message: 'Not registered as agent' });
        return;
      }
      
      const messageId = `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
      
      // Save message to database
      const message = await Message.create({
        messageId,
        fromAgent: fromAgentId,
        toAgent: to,
        content,
        type,
        metadata: {
          ...metadata,
          socketId: socket.id
        }
      });
      
      const messageData = {
        id: message.id,
        messageId: message.message_id,
        from: fromAgentId,
        to: to,
        content,
        type,
        metadata,
        timestamp: message.created_at
      };
      
      // Send to recipient if online
      const recipientSocket = connectedAgents.get(to);
      if (recipientSocket) {
        recipientSocket.emit('message', messageData);
        await Message.markAsDelivered(message.id);
        
        // Also mark as read immediately if it's a direct response
        if (type === 'command') {
          await Message.markAsRead(message.id);
        }
      } else {
        // Store for later delivery
        logger.info(`Message queued for offline agent: ${to}`);
      }
      
      // Confirm delivery to sender
      socket.emit('message_sent', {
        success: true,
        messageId: message.message_id,
        delivered: !!recipientSocket
      });
      
    } catch (error) {
      logger.error('Error sending message:', error);
      socket.emit('error', { message: 'Failed to send message', error: error.message });
    }
  }
  
  handleTyping(socket, { to, isTyping }) {
    const fromAgentId = socketToAgent.get(socket.id);
    if (!fromAgentId) return;
    
    const recipientSocket = connectedAgents.get(to);
    if (recipientSocket) {
      recipientSocket.emit('typing', {
        from: fromAgentId,
        isTyping
      });
    }
  }
  
  async handleHeartbeat(socket, data) {
    const agentId = socketToAgent.get(socket.id);
    if (agentId) {
      await Agent.heartbeat(agentId);
      socket.emit('heartbeat_ack', { timestamp: new Date().toISOString() });
    }
  }
  
  async handleLogMemory(socket, { memoryType, content, context = {}, importance = 1 }) {
    try {
      const agentId = socketToAgent.get(socket.id);
      if (!agentId) {
        socket.emit('error', { message: 'Not registered as agent' });
        return;
      }
      
      const memory = await AgentMemory.log({
        agentId,
        memoryType,
        content,
        context,
        importance
      });
      
      socket.emit('memory_logged', {
        success: true,
        memoryId: memory.id
      });
      
      // If it's a high-importance need, notify master
      if (memoryType === 'need' && importance >= 4) {
        this.io.to('agent:master').emit('agent_need', {
          agentId,
          need: content,
          importance,
          memoryId: memory.id
        });
      }
      
    } catch (error) {
      logger.error('Error logging memory:', error);
      socket.emit('error', { message: 'Failed to log memory', error: error.message });
    }
  }
  
  async handleCreateJob(socket, { title, description, priority = 2, assignTo }) {
    try {
      const fromAgentId = socketToAgent.get(socket.id);
      if (!fromAgentId) {
        socket.emit('error', { message: 'Not registered as agent' });
        return;
      }
      
      const job = await AgentJob.create({
        agentId: assignTo || fromAgentId,
        title,
        description,
        priority,
        assignedBy: fromAgentId
      });
      
      socket.emit('job_created', {
        success: true,
        job: {
          id: job.id,
          jobId: job.job_id,
          title: job.title,
          status: job.status,
          priority: job.priority
        }
      });
      
      // Notify assigned agent if online
      if (assignTo && assignTo !== fromAgentId) {
        const assigneeSocket = connectedAgents.get(assignTo);
        if (assigneeSocket) {
          assigneeSocket.emit('new_job', {
            jobId: job.job_id,
            title,
            description,
            priority,
            assignedBy: fromAgentId
          });
        }
      }
      
    } catch (error) {
      logger.error('Error creating job:', error);
      socket.emit('error', { message: 'Failed to create job', error: error.message });
    }
  }
  
  async handleUpdateJob(socket, { jobId, status, result }) {
    try {
      const agentId = socketToAgent.get(socket.id);
      if (!agentId) {
        socket.emit('error', { message: 'Not registered as agent' });
        return;
      }
      
      const job = await AgentJob.updateStatus(jobId, status, result);
      
      socket.emit('job_updated', {
        success: true,
        job: {
          jobId: job.job_id,
          status: job.status,
          completedAt: job.completed_at
        }
      });
      
      // Notify assigner if job is completed
      if (job.assigned_by && job.assigned_by !== agentId) {
        const assignerSocket = connectedAgents.get(job.assigned_by);
        if (assignerSocket) {
          assignerSocket.emit('job_status', {
            jobId: job.job_id,
            status,
            completedBy: agentId,
            result
          });
        }
      }
      
    } catch (error) {
      logger.error('Error updating job:', error);
      socket.emit('error', { message: 'Failed to update job', error: error.message });
    }
  }
  
  async handleGetContext(socket, data) {
    try {
      const agentId = socketToAgent.get(socket.id);
      if (!agentId) {
        socket.emit('error', { message: 'Not registered as agent' });
        return;
      }
      
      const context = await AgentMemory.getContext(agentId);
      const pendingJobs = await AgentJob.findForAgent(agentId, { status: 'pending' });
      const needs = await AgentMemory.getNeeds(agentId);
      
      socket.emit('context', {
        agentId,
        memories: context,
        pendingJobs,
        needs,
        timestamp: new Date().toISOString()
      });
      
    } catch (error) {
      logger.error('Error getting context:', error);
      socket.emit('error', { message: 'Failed to get context', error: error.message });
    }
  }
  
  async handleDisconnect(socket) {
    const agentId = socketToAgent.get(socket.id);
    
    if (agentId) {
      await Agent.updateStatus(agentId, 'offline');
      connectedAgents.delete(agentId);
      socketToAgent.delete(socket.id);
      
      logger.info(`Agent disconnected: ${agentId}`);
      
      // Broadcast offline status
      this.io.emit('agent_status', {
        agentId,
        status: 'offline',
        timestamp: new Date().toISOString()
      });
    } else {
      logger.info(`Client disconnected: ${socket.id}`);
    }
  }
  
  startHeartbeatCheck() {
    setInterval(async () => {
      try {
        const offlineAgents = await Agent.findOfflineAgents(config.websocket.agentTimeout);
        
        for (const agent of offlineAgents) {
          await Agent.updateStatus(agent.agent_id, 'offline');
          connectedAgents.delete(agent.agent_id);
          
          this.io.emit('agent_status', {
            agentId: agent.agent_id,
            status: 'offline',
            timestamp: new Date().toISOString()
          });
          
          logger.warn(`Agent marked offline (timeout): ${agent.agent_id}`);
        }
      } catch (error) {
        logger.error('Error in heartbeat check:', error);
      }
    }, config.websocket.heartbeatInterval);
  }
  
  // Public methods for external use
  broadcastToAgent(agentId, event, data) {
    const socket = connectedAgents.get(agentId);
    if (socket) {
      socket.emit(event, data);
      return true;
    }
    return false;
  }
  
  broadcastToAll(event, data) {
    this.io.emit(event, data);
  }
  
  getConnectedAgents() {
    return Array.from(connectedAgents.keys());
  }
}

module.exports = WebSocketServer;
