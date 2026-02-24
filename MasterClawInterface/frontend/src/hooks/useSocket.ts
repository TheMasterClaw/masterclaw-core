import { useEffect, useRef, useState, useCallback } from 'react';
import { io, Socket } from 'socket.io-client';
import type { 
  Message, 
  Agent, 
  User, 
  AgentJob, 
  AgentMemory, 
  AgentBlocker,
  AgentDesire,
  AgentStatusUpdate 
} from '../types';

const SOCKET_URL = import.meta.env.VITE_SOCKET_URL || 'ws://localhost:3001';

interface UseSocketProps {
  user: User;
  onMessage?: (message: Message) => void;
  onAgentUpdate?: (agent: Agent) => void;
  onAgentStatus?: (update: AgentStatusUpdate) => void;
  onJobCreated?: (job: AgentJob) => void;
  onJobUpdated?: (job: AgentJob) => void;
  onAgentNeed?: (data: { agentId: string; need: string; importance: number }) => void;
  onAgentBlocker?: (data: { agentId: string; blocker: AgentBlocker }) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
}

export function useSocket({ 
  user, 
  onMessage, 
  onAgentUpdate,
  onAgentStatus,
  onJobCreated,
  onJobUpdated,
  onAgentNeed,
  onAgentBlocker,
  onConnect, 
  onDisconnect 
}: UseSocketProps) {
  const socketRef = useRef<Socket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const [connectedAgents, setConnectedAgents] = useState<string[]>([]);

  useEffect(() => {
    const socket = io(SOCKET_URL, {
      auth: { userId: user.id, userName: user.name, role: user.role },
      reconnection: true,
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
    });

    socketRef.current = socket;

    socket.on('connect', () => {
      console.log('[MasterClaw] Connected to server');
      setIsConnected(true);
      setConnectionError(null);
      onConnect?.();
    });

    socket.on('disconnect', (reason) => {
      console.log('[MasterClaw] Disconnected:', reason);
      setIsConnected(false);
      onDisconnect?.();
    });

    socket.on('connect_error', (error) => {
      console.error('[MasterClaw] Connection error:', error);
      setConnectionError(error.message);
    });

    // Handle incoming messages
    socket.on('message', (message: Message) => {
      console.log('[MasterClaw] Message received:', message);
      onMessage?.(message);
    });

    // Handle unread messages on connect
    socket.on('unread_messages', (messages: Message[]) => {
      console.log('[MasterClaw] Unread messages:', messages.length);
      messages.forEach(msg => onMessage?.(msg));
    });

    // Agent status updates
    socket.on('agent_status', (data: AgentStatusUpdate) => {
      console.log('[MasterClaw] Agent status:', data);
      onAgentStatus?.(data);
      
      // Update connected agents list
      if (data.status === 'online') {
        setConnectedAgents(prev => [...new Set([...prev, data.agentId])]);
      } else if (data.status === 'offline') {
        setConnectedAgents(prev => prev.filter(id => id !== data.agentId));
      }
    });

    // Agent registered
    socket.on('registered', (data: { success: boolean; agent: Agent }) => {
      console.log('[MasterClaw] Agent registered:', data);
      if (data.success) {
        onAgentUpdate?.(data.agent);
      }
    });

    // Job created
    socket.on('job_created', (data: { success: boolean; job: AgentJob }) => {
      console.log('[MasterClaw] Job created:', data);
      if (data.success) {
        onJobCreated?.(data.job);
      }
    });

    // Job updated
    socket.on('job_updated', (data: { success: boolean; job: Partial<AgentJob> }) => {
      console.log('[MasterClaw] Job updated:', data);
      if (data.success && data.job) {
        onJobUpdated?.(data.job as AgentJob);
      }
    });

    // New job assigned
    socket.on('new_job', (job: AgentJob) => {
      console.log('[MasterClaw] New job assigned:', job);
      onJobCreated?.(job);
    });

    // Job status update
    socket.on('job_status', (data: { jobId: string; status: string; completedBy?: string; result?: string }) => {
      console.log('[MasterClaw] Job status:', data);
    });

    // Memory logged
    socket.on('memory_logged', (data: { success: boolean; memoryId: number }) => {
      console.log('[MasterClaw] Memory logged:', data);
    });

    // Agent need (high importance)
    socket.on('agent_need', (data: { agentId: string; need: string; importance: number; memoryId: number }) => {
      console.log('[MasterClaw] Agent need:', data);
      onAgentNeed?.(data);
    });

    // Agent blocker
    socket.on('agent_blocker', (data: { agentId: string; blocker: AgentBlocker }) => {
      console.log('[MasterClaw] Agent blocker:', data);
      onAgentBlocker?.(data);
    });

    // Blocker resolved
    socket.on('blocker_resolved', (data: { agentId: string; blockerId: string; resolution: string }) => {
      console.log('[MasterClaw] Blocker resolved:', data);
    });

    // Agent desire
    socket.on('agent_desire', (data: { agentId: string; desire: AgentDesire }) => {
      console.log('[MasterClaw] Agent desire:', data);
    });

    // Context response
    socket.on('context', (data: { 
      agentId: string; 
      memories: AgentMemory[]; 
      pendingJobs: AgentJob[]; 
      needs: AgentMemory[];
      timestamp: string;
    }) => {
      console.log('[MasterClaw] Context received:', data);
    });

    // Error handling
    socket.on('error', (error: { message: string; error?: string }) => {
      console.error('[MasterClaw] Socket error:', error);
      setConnectionError(error.message);
    });

    return () => {
      socket.disconnect();
    };
  }, [user.id, user.name, user.role]);

  // Send a message to another agent
  const sendMessage = useCallback((to: string, content: string, type: string = 'text', metadata?: Record<string, unknown>) => {
    if (!socketRef.current?.connected) {
      console.error('[MasterClaw] Cannot send message: not connected');
      return false;
    }

    socketRef.current.emit('send_message', {
      to,
      content,
      type,
      metadata: metadata || {}
    });
    return true;
  }, []);

  // Send typing indicator
  const sendTyping = useCallback((to: string, isTyping: boolean) => {
    socketRef.current?.emit('typing', { to, isTyping });
  }, []);

  // Log memory/thought
  const logMemory = useCallback((memoryType: string, content: string, context?: Record<string, unknown>, importance: number = 1) => {
    socketRef.current?.emit('log_memory', {
      memoryType,
      content,
      context: context || {},
      importance
    });
  }, []);

  // Create a job
  const createJob = useCallback((title: string, description: string, priority: number = 2, assignTo?: string) => {
    socketRef.current?.emit('create_job', {
      title,
      description,
      priority,
      assignTo
    });
  }, []);

  // Update job status
  const updateJob = useCallback((jobId: string, status: string, result?: string) => {
    socketRef.current?.emit('update_job', {
      jobId,
      status,
      result
    });
  }, []);

  // Get agent context
  const getContext = useCallback(() => {
    socketRef.current?.emit('get_context', {});
  }, []);

  // Register as an agent
  const registerAgent = useCallback((agentId: string, name: string, type: string = 'subagent', capabilities: string[] = []) => {
    socketRef.current?.emit('register_agent', {
      agentId,
      name,
      type,
      capabilities
    });
  }, []);

  // Send heartbeat
  const sendHeartbeat = useCallback((data?: Record<string, unknown>) => {
    socketRef.current?.emit('heartbeat', data || {});
  }, []);

  // Listen for typing indicators
  const onTyping = useCallback((callback: (data: { from: string; isTyping: boolean }) => void) => {
    socketRef.current?.on('typing', callback);
    return () => {
      socketRef.current?.off('typing', callback);
    };
  }, []);

  return {
    socket: socketRef.current,
    isConnected,
    connectionError,
    connectedAgents,
    sendMessage,
    sendTyping,
    logMemory,
    createJob,
    updateJob,
    getContext,
    registerAgent,
    sendHeartbeat,
    onTyping,
  };
}