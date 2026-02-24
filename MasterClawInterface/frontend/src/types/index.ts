// Types matching the backend API

export interface Agent {
  id: string;
  agent_id: string;
  name: string;
  status: 'online' | 'offline' | 'busy' | 'error' | 'away';
  type: string;
  capabilities: string[];
  metadata: Record<string, unknown>;
  current_job?: string;
  socket_id?: string;
  last_active?: string;
  last_heartbeat?: string;
  created_at?: string;
  updated_at?: string;
}

export interface AgentJob {
  id?: number;
  job_id: string;
  agent_id: string;
  title: string;
  description?: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed' | 'cancelled';
  priority: number;
  assigned_by?: string;
  result?: string;
  started_at?: string;
  completed_at?: string;
  created_at?: string;
  updated_at?: string;
}

export interface AgentMemory {
  id?: number;
  agent_id: string;
  memory_type: 'thought' | 'observation' | 'decision' | 'need' | 'blocker' | 'insight';
  content: string;
  context: Record<string, unknown>;
  importance: number;
  related_message_id?: number;
  related_message_content?: string;
  created_at?: string;
}

export interface AgentBlocker {
  blocker_id: string;
  agent_id: string;
  description: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  created_at: string;
  resolved_at?: string;
  resolved_by?: string;
  resolution?: string;
}

export interface AgentDesire {
  desire_id: string;
  agent_id: string;
  description: string;
  priority: 'high' | 'medium' | 'low';
  created_at: string;
  fulfilled_at?: string;
  fulfilled_by?: string;
}

export interface AgentDesire {
  desire_id: string;
  agent_id: string;
  description: string;
  priority: 'high' | 'medium' | 'low';
  created_at: string;
  fulfilled_at?: string;
  fulfilled_by?: string;
}

export interface Message {
  id?: number;
  message_id: string;
  from_agent: string;
  to_agent: string;
  content: string;
  type: 'text' | 'command' | 'system' | 'thought' | 'broadcast';
  metadata: Record<string, unknown>;
  is_read: boolean;
  is_delivered: boolean;
  created_at: string;
}

export interface ChatThread {
  agentId: string;
  messages: Message[];
  unreadCount: number;
  lastMessageAt?: string;
}

export interface User {
  id: string;
  name: string;
  role: 'rex' | 'admin' | 'observer';
  avatar?: string;
}

export interface ServerStats {
  agents: {
    total: number;
    online: number;
    offline: number;
    busy: number;
  };
  jobs: {
    pending: number;
    inProgress: number;
  };
  connectedNow: string[];
}

// Frontend display types (transformed from API types)
export interface DisplayAgent {
  id: string;
  name: string;
  status: 'online' | 'offline' | 'busy' | 'error' | 'away';
  type: string;
  capabilities: string[];
  currentJob?: string;
  lastSeen?: string;
  memory?: {
    thoughts: DisplayThought[];
    jobs: DisplayJob[];
    needs: string[];
    blockers: DisplayBlocker[];
    context: Record<string, unknown>;
  };
}

export interface DisplayThought {
  id: string;
  content: string;
  timestamp: string;
  category: 'thought' | 'observation' | 'decision' | 'need' | 'blocker' | 'insight';
}

export interface DisplayJob {
  id: string;
  title: string;
  description?: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed' | 'cancelled';
  priority: number;
  progress?: number;
  startedAt?: string;
  completedAt?: string;
  result?: string;
}

export interface DisplayBlocker {
  id: string;
  description: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  createdAt: string;
  resolvedAt?: string;
}

// WebSocket event types
export interface WebSocketMessage {
  type: string;
  message?: Message;
  agent?: Agent;
  agentId?: string;
  status?: string;
  currentJob?: string;
  job?: AgentJob;
  memory?: AgentMemory;
  need?: string;
  blocker?: AgentBlocker;
  content?: string;
  timestamp?: string;
}

export interface AgentStatusUpdate {
  agentId: string;
  status: string;
  timestamp: string;
}