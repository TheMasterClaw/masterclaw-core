import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:3001';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Agent API
export const agentApi = {
  // Get all agents
  getAll: async (params?: { status?: string; type?: string; limit?: number; offset?: number }) => {
    const { data } = await api.get('/api/agents', { params });
    return data;
  },

  // Get agent by ID
  getById: async (agentId: string) => {
    const { data } = await api.get(`/api/agents/${agentId}`);
    return data;
  },

  // Register new agent
  create: async (agentData: {
    agentId: string;
    name?: string;
    type?: string;
    capabilities?: string[];
    metadata?: Record<string, unknown>;
  }) => {
    const { data } = await api.post('/api/agents', agentData);
    return data;
  },

  // Update agent
  update: async (agentId: string, updates: Record<string, unknown>) => {
    const { data } = await api.put(`/api/agents/${agentId}`, updates);
    return data;
  },

  // Delete agent
  delete: async (agentId: string) => {
    const { data } = await api.delete(`/api/agents/${agentId}`);
    return data;
  },

  // Get agent stats
  getStats: async (agentId: string) => {
    const { data } = await api.get(`/api/agents/${agentId}/stats`);
    return data;
  },

  // Get agent memory
  getMemory: async (agentId: string, params?: { types?: string; limit?: number; minImportance?: number }) => {
    const { data } = await api.get(`/api/agents/${agentId}/memory`, { params });
    return data;
  },

  // Get agent needs
  getNeeds: async (agentId: string) => {
    const { data } = await api.get(`/api/agents/${agentId}/needs`);
    return data;
  },

  // Get agent jobs
  getJobs: async (agentId: string, params?: { status?: string; limit?: number }) => {
    const { data } = await api.get(`/api/agents/${agentId}/jobs`, { params });
    return data;
  },
};

// Message API
export const messageApi = {
  // Get conversation between two agents
  getConversation: async (agent1: string, agent2: string, params?: { limit?: number; offset?: number }) => {
    const { data } = await api.get(`/api/messages/conversation/${agent1}/${agent2}`, { params });
    return data;
  },

  // Get messages for an agent
  getForAgent: async (agentId: string, params?: { limit?: number; offset?: number; unreadOnly?: boolean }) => {
    const { data } = await api.get(`/api/messages/agent/${agentId}`, { params });
    return data;
  },

  // Send message via REST (fallback)
  send: async (messageData: {
    fromAgent: string;
    toAgent: string;
    content: string;
    type?: string;
    metadata?: Record<string, unknown>;
  }) => {
    const { data } = await api.post('/api/messages', messageData);
    return data;
  },

  // Mark message as read
  markAsRead: async (messageId: string) => {
    const { data } = await api.put(`/api/messages/${messageId}/read`);
    return data;
  },

  // Get unread count
  getUnreadCount: async (agentId: string) => {
    const { data } = await api.get(`/api/messages/agent/${agentId}/unread`);
    return data;
  },
};

// Stats API
export const statsApi = {
  // Get server stats
  getStats: async () => {
    const { data } = await api.get('/api/stats');
    return data;
  },

  // Health check
  healthCheck: async () => {
    const { data } = await api.get('/health');
    return data;
  },
};

// Broadcast API (admin)
export const broadcastApi = {
  // Send broadcast message
  send: async (message: string, type: string = 'announcement') => {
    const { data } = await api.post('/api/broadcast', { message, type });
    return data;
  },
};

export default api;