/**
 * MasterClaw Agent Client SDK
 * 
 * Use this SDK to connect agents to the MasterClaw Chat Interface.
 * 
 * @example
 * const agent = new MasterClawAgent({
 *   agentId: 'my-agent-001',
 *   name: 'My Agent',
 *   type: 'worker',
 *   serverUrl: 'http://localhost:3001'
 * });
 * 
 * await agent.connect();
 * 
 * // Send a message to Rex
 * await agent.messageRex('Hello! Task completed.');
 * 
 * // Log a thought
 * await agent.logThought('Processing data...', 2);
 * 
 * // Create a job
 * await agent.createJob({
 *   title: 'Analyze logs',
 *   description: 'Check error logs',
 *   priority: 3
 * });
 */

const io = require('socket.io-client');
const axios = require('axios');
const EventEmitter = require('events');

class MasterClawAgent extends EventEmitter {
  /**
   * Create a new MasterClaw Agent client
   * @param {Object} options - Configuration options
   * @param {string} options.agentId - Unique identifier for this agent
   * @param {string} options.name - Human-readable name
   * @param {string} [options.type='subagent'] - Agent type
   * @param {string[]} [options.capabilities=[]] - Agent capabilities
   * @param {string} [options.serverUrl='http://localhost:3001'] - Server URL
   * @param {string} [options.authToken] - Authentication token (optional)
   */
  constructor(options = {}) {
    super();
    
    this.agentId = options.agentId || this._generateId();
    this.name = options.name || this.agentId;
    this.type = options.type || 'subagent';
    this.capabilities = options.capabilities || [];
    this.serverUrl = options.serverUrl || 'http://localhost:3001';
    this.authToken = options.authToken;
    
    this.socket = null;
    this.connected = false;
    this.registered = false;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = options.maxReconnectAttempts || 10;
    
    // Message queue for offline messages
    this.messageQueue = [];
    
    // Pending jobs
    this.jobs = new Map();
  }
  
  /**
   * Generate a random agent ID
   * @private
   */
  _generateId() {
    return `agent-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }
  
  /**
   * Connect to the MasterClaw server
   * @returns {Promise<void>}
   */
  async connect() {
    return new Promise((resolve, reject) => {
      const socketOptions = {
        reconnection: true,
        reconnectionAttempts: this.maxReconnectAttempts,
        reconnectionDelay: 1000,
        reconnectionDelayMax: 5000,
        randomizationFactor: 0.5,
        timeout: 20000,
      };
      
      if (this.authToken) {
        socketOptions.auth = { token: this.authToken };
      }
      
      this.socket = io(this.serverUrl, socketOptions);
      
      // Connection events
      this.socket.on('connect', () => {
        this.connected = true;
        this.reconnectAttempts = 0;
        this.emit('connected');
        
        // Register with the server
        this._register();
        resolve();
      });
      
      this.socket.on('disconnect', (reason) => {
        this.connected = false;
        this.registered = false;
        this.emit('disconnected', reason);
      });
      
      this.socket.on('connect_error', (error) => {
        this.reconnectAttempts++;
        this.emit('error', error);
        
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
          reject(new Error(`Failed to connect after ${this.maxReconnectAttempts} attempts`));
        }
      });
      
      // Registration confirmation
      this.socket.on('registered', (data) => {
        this.registered = true;
        this.emit('registered', data);
        
        // Process queued messages
        this._processMessageQueue();
      });
      
      // Incoming message
      this.socket.on('message', (data) => {
        this.emit('message', data);
        this._handleMessage(data);
      });
      
      // Typing indicator
      this.socket.on('typing', (data) => {
        this.emit('typing', data);
      });
      
      // Agent status updates
      this.socket.on('agent_status', (data) => {
        this.emit('agentStatus', data);
      });
      
      // New job assigned
      this.socket.on('new_job', (data) => {
        this.jobs.set(data.jobId, data);
        this.emit('newJob', data);
      });
      
      // Job status update
      this.socket.on('job_status', (data) => {
        this.emit('jobStatus', data);
      });
      
      // Broadcast message
      this.socket.on('broadcast', (data) => {
        this.emit('broadcast', data);
      });
      
      // Heartbeat acknowledgment
      this.socket.on('heartbeat_ack', (data) => {
        this.emit('heartbeat', data);
      });
      
      // Error handling
      this.socket.on('error', (error) => {
        this.emit('error', error);
      });
      
      // Context response
      this.socket.on('context', (data) => {
        this.emit('context', data);
      });
    });
  }
  
  /**
   * Register with the server
   * @private
   */
  _register() {
    this.socket.emit('register_agent', {
      agentId: this.agentId,
      name: this.name,
      type: this.type,
      capabilities: this.capabilities
    });
  }
  
  /**
   * Process queued messages
   * @private
   */
  _processMessageQueue() {
    while (this.messageQueue.length > 0) {
      const msg = this.messageQueue.shift();
      this.sendMessage(msg.to, msg.content, msg.type, msg.metadata);
    }
  }
  
  /**
   * Handle incoming message
   * @private
   */
  _handleMessage(data) {
    // Auto-log receipt as observation
    if (data.type === 'command') {
      this.logThought(
        `Received command from ${data.from}: ${data.content}`,
        3,
        { command: data.content, from: data.from }
      );
    }
  }
  
  /**
   * Send a message to another agent
   * @param {string} to - Recipient agent ID
   * @param {string} content - Message content
   * @param {string} [type='text'] - Message type
   * @param {Object} [metadata={}] - Additional metadata
   * @returns {boolean} Success status
   */
  sendMessage(to, content, type = 'text', metadata = {}) {
    if (!this.connected) {
      // Queue message for later
      this.messageQueue.push({ to, content, type, metadata });
      this.emit('queued', { to, content, type });
      return false;
    }
    
    this.socket.emit('send_message', {
      to,
      content,
      type,
      metadata
    });
    
    return true;
  }
  
  /**
   * Send a message to Rex (convenience method)
   * @param {string} content - Message content
   * @param {string} [type='text'] - Message type
   * @returns {boolean} Success status
   */
  messageRex(content, type = 'text') {
    return this.sendMessage('rex', content, type);
  }
  
  /**
   * Send a message to Master agent
   * @param {string} content - Message content
   * @param {string} [type='text'] - Message type
   * @returns {boolean} Success status
   */
  messageMaster(content, type = 'text') {
    return this.sendMessage('master', content, type);
  }
  
  /**
   * Broadcast a message to all agents
   * @param {string} content - Message content
   * @returns {boolean} Success status
   */
  broadcast(content) {
    if (!this.connected) {
      this.emit('error', new Error('Cannot broadcast: not connected'));
      return false;
    }
    
    this.socket.emit('broadcast', { content });
    return true;
  }
  
  /**
   * Send typing indicator
   * @param {string} to - Recipient agent ID
   * @param {boolean} isTyping - Typing status
   */
  setTyping(to, isTyping) {
    if (!this.connected) return;
    
    this.socket.emit('typing', { to, isTyping });
  }
  
  /**
   * Log a thought/memory
   * @param {string} content - Thought content
   * @param {number} [importance=1] - Importance level (1-5)
   * @param {Object} [context={}] - Additional context
   * @returns {Promise<Object>} Logged memory
   */
  async logThought(content, importance = 1, context = {}) {
    if (!this.connected) {
      throw new Error('Cannot log thought: not connected');
    }
    
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        reject(new Error('Timeout logging thought'));
      }, 5000);
      
      this.socket.once('memory_logged', (data) => {
        clearTimeout(timeout);
        resolve(data);
      });
      
      this.socket.emit('log_memory', {
        memoryType: 'thought',
        content,
        importance,
        context
      });
    });
  }
  
  /**
   * Log a need (something the agent needs help with)
   * @param {string} content - Description of the need
   * @param {number} [importance=3] - Importance level (1-5)
   * @param {Object} [context={}] - Additional context
   * @returns {Promise<Object>} Logged need
   */
  async logNeed(content, importance = 3, context = {}) {
    if (!this.connected) {
      throw new Error('Cannot log need: not connected');
    }
    
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        reject(new Error('Timeout logging need'));
      }, 5000);
      
      this.socket.once('memory_logged', (data) => {
        clearTimeout(timeout);
        resolve(data);
      });
      
      this.socket.emit('log_memory', {
        memoryType: 'need',
        content,
        importance,
        context
      });
    });
  }
  
  /**
   * Log an observation
   * @param {string} content - Observation content
   * @param {number} [importance=2] - Importance level (1-5)
   * @param {Object} [context={}] - Additional context
   * @returns {Promise<Object>} Logged observation
   */
  async logObservation(content, importance = 2, context = {}) {
    return this._logMemory('observation', content, importance, context);
  }
  
  /**
   * Log a decision
   * @param {string} content - Decision description
   * @param {number} [importance=2] - Importance level (1-5)
   * @param {Object} [context={}] - Additional context
   * @returns {Promise<Object>} Logged decision
   */
  async logDecision(content, importance = 2, context = {}) {
    return this._logMemory('decision', content, importance, context);
  }
  
  /**
   * Internal method to log memory
   * @private
   */
  _logMemory(memoryType, content, importance, context) {
    if (!this.connected) {
      throw new Error('Cannot log memory: not connected');
    }
    
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        reject(new Error('Timeout logging memory'));
      }, 5000);
      
      this.socket.once('memory_logged', (data) => {
        clearTimeout(timeout);
        resolve(data);
      });
      
      this.socket.emit('log_memory', {
        memoryType,
        content,
        importance,
        context
      });
    });
  }
  
  /**
   * Create a new job/task
   * @param {Object} job - Job details
   * @param {string} job.title - Job title
   * @param {string} [job.description] - Job description
   * @param {number} [job.priority=2] - Priority (1-5)
   * @param {string} [job.assignTo] - Agent to assign to (defaults to self)
   * @returns {Promise<Object>} Created job
   */
  async createJob({ title, description = '', priority = 2, assignTo = null }) {
    if (!this.connected) {
      throw new Error('Cannot create job: not connected');
    }
    
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        reject(new Error('Timeout creating job'));
      }, 5000);
      
      this.socket.once('job_created', (data) => {
        clearTimeout(timeout);
        if (data.success) {
          this.jobs.set(data.job.jobId, data.job);
        }
        resolve(data);
      });
      
      this.socket.emit('create_job', {
        title,
        description,
        priority,
        assignTo: assignTo || this.agentId
      });
    });
  }
  
  /**
   * Update job status
   * @param {string} jobId - Job ID
   * @param {string} status - New status (pending, in_progress, completed, failed, cancelled)
   * @param {Object} [result] - Job result data
   * @returns {Promise<Object>} Updated job
   */
  async updateJob(jobId, status, result = null) {
    if (!this.connected) {
      throw new Error('Cannot update job: not connected');
    }
    
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        reject(new Error('Timeout updating job'));
      }, 5000);
      
      this.socket.once('job_updated', (data) => {
        clearTimeout(timeout);
        resolve(data);
      });
      
      this.socket.emit('update_job', { jobId, status, result });
    });
  }
  
  /**
   * Get agent context (memories, jobs, needs)
   * @returns {Promise<Object>} Agent context
   */
  async getContext() {
    if (!this.connected) {
      throw new Error('Cannot get context: not connected');
    }
    
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        reject(new Error('Timeout getting context'));
      }, 10000);
      
      this.socket.once('context', (data) => {
        clearTimeout(timeout);
        resolve(data);
      });
      
      this.socket.emit('get_context', {});
    });
  }
  
  /**
   * Send heartbeat/ping
   */
  heartbeat() {
    if (!this.connected) return;
    this.socket.emit('heartbeat', { timestamp: Date.now() });
  }
  
  /**
   * Start automatic heartbeat
   * @param {number} intervalMs - Interval in milliseconds
   */
  startHeartbeat(intervalMs = 30000) {
    this.stopHeartbeat();
    this.heartbeatInterval = setInterval(() => {
      this.heartbeat();
    }, intervalMs);
  }
  
  /**
   * Stop automatic heartbeat
   */
  stopHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }
  
  /**
   * Update agent status
   * @param {string} status - New status (online, offline, busy, away)
   */
  setStatus(status) {
    if (!this.connected) return;
    // Status updates are handled automatically by the server
    // This method is for explicit status changes
    this.socket.emit('status_change', { status });
  }
  
  /**
   * Disconnect from server
   */
  disconnect() {
    this.stopHeartbeat();
    
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
    
    this.connected = false;
    this.registered = false;
  }
  
  /**
   * Check if connected and registered
   * @returns {boolean}
   */
  isReady() {
    return this.connected && this.registered;
  }
  
  /**
   * Get agent info
   * @returns {Object}
   */
  getInfo() {
    return {
      agentId: this.agentId,
      name: this.name,
      type: this.type,
      capabilities: this.capabilities,
      connected: this.connected,
      registered: this.registered,
      serverUrl: this.serverUrl
    };
  }
}

module.exports = MasterClawAgent;
