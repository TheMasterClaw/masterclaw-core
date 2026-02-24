import { useState, useCallback, useEffect } from 'react';
import { Agent, Message, User, ChatThread, ServerStats, AgentJob, AgentStatusUpdate } from './types';
import { agentApi, messageApi, statsApi } from './api';
import { useSocket } from './hooks/useSocket';
import { Header } from './components/Header';
import { AgentList } from './components/AgentList';
import { ChatWindow } from './components/ChatWindow';
import { AgentMemoryPanel } from './components/AgentMemoryPanel';
import { Dashboard } from './components/Dashboard';
import './index.css';

// Rex's user profile
const REX_USER: User = {
  id: 'rex-master',
  name: 'Rex',
  role: 'rex'
};

function App() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);
  const [threads, setThreads] = useState<Record<string, ChatThread>>({});
  const [unreadCounts, setUnreadCounts] = useState<Record<string, number>>({});
  const [showMemoryPanel, setShowMemoryPanel] = useState(false);
  const [showDashboard, setShowDashboard] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [serverStats, setServerStats] = useState<ServerStats | null>(null);
  const [isLoadingAgents, setIsLoadingAgents] = useState(false);
  const [isLoadingMessages, setIsLoadingMessages] = useState(false);

  const selectedAgent = agents.find(a => a.agent_id === selectedAgentId) || null;
  const currentThread = selectedAgentId ? threads[selectedAgentId] : null;
  const messages = currentThread?.messages || [];

  // Load initial data
  const loadAgents = useCallback(async () => {
    setIsLoadingAgents(true);
    try {
      const response = await agentApi.getAll();
      setAgents(response.agents || []);
    } catch (error) {
      console.error('Failed to load agents:', error);
    } finally {
      setIsLoadingAgents(false);
    }
  }, []);

  const loadMessages = useCallback(async (agentId: string) => {
    setIsLoadingMessages(true);
    try {
      const response = await messageApi.getConversation(REX_USER.id, agentId, { limit: 100 });
      setThreads(prev => ({
        ...prev,
        [agentId]: {
          agentId,
          messages: response.messages || [],
          unreadCount: 0
        }
      }));
    } catch (error) {
      console.error('Failed to load messages:', error);
    } finally {
      setIsLoadingMessages(false);
    }
  }, []);

  const loadStats = useCallback(async () => {
    try {
      const stats = await statsApi.getStats();
      setServerStats(stats);
    } catch (error) {
      console.error('Failed to load stats:', error);
    }
  }, []);

  // Initial load
  useEffect(() => {
    loadAgents();
    loadStats();
    
    // Refresh stats periodically
    const statsInterval = setInterval(loadStats, 30000);
    return () => clearInterval(statsInterval);
  }, [loadAgents, loadStats]);

  // Load messages when agent is selected
  useEffect(() => {
    if (selectedAgentId && !threads[selectedAgentId]) {
      loadMessages(selectedAgentId);
    }
  }, [selectedAgentId, threads, loadMessages]);

  // Handle incoming messages
  const handleMessage = useCallback((message: Message) => {
    // Determine which agent this message is from/to
    const agentId = message.from_agent === REX_USER.id ? message.to_agent : message.from_agent;
    
    setThreads(prev => {
      const existingThread = prev[agentId] || {
        agentId,
        messages: [],
        unreadCount: 0
      };

      // Check if message already exists
      const messageExists = existingThread.messages.some(m => 
        m.message_id === message.message_id || m.id === message.id
      );

      if (messageExists) {
        return prev;
      }

      const isFromSelected = agentId === selectedAgentId;

      return {
        ...prev,
        [agentId]: {
          ...existingThread,
          messages: [...existingThread.messages, message],
          lastMessageAt: message.created_at,
          unreadCount: isFromSelected ? 0 : existingThread.unreadCount + 1
        }
      };
    });

    // Update unread counts
    if (agentId !== selectedAgentId) {
      setUnreadCounts(prev => ({
        ...prev,
        [agentId]: (prev[agentId] || 0) + 1
      }));
    }

    // Show typing indicator briefly
    if (message.from_agent !== REX_USER.id) {
      setIsTyping(true);
      setTimeout(() => setIsTyping(false), 2000);
    }
  }, [selectedAgentId]);

  // Handle agent status updates
  const handleAgentStatus = useCallback((update: AgentStatusUpdate) => {
    setAgents(prev => 
      prev.map(agent => 
        agent.agent_id === update.agentId 
          ? { ...agent, status: update.status as Agent['status'] }
          : agent
      )
    );
  }, []);

  // Handle job creation
  const handleJobCreated = useCallback((job: AgentJob) => {
    console.log('Job created:', job);
    // Could show a notification here
  }, []);

  // Handle job updates
  const handleJobUpdated = useCallback((job: AgentJob) => {
    console.log('Job updated:', job);
  }, []);

  // Handle agent needs
  const handleAgentNeed = useCallback((data: { agentId: string; need: string; importance: number }) => {
    console.log('Agent need:', data);
    // Could show a notification for high-importance needs
  }, []);

  // Handle agent blockers
  const handleAgentBlocker = useCallback((data: { agentId: string; blocker: unknown }) => {
    console.log('Agent blocker:', data);
    // Could show a notification for blockers
  }, []);

  // Setup WebSocket
  const {
    isConnected,
    connectionError,
    sendMessage: sendWsMessage,
  } = useSocket({
    user: REX_USER,
    onMessage: handleMessage,
    onAgentStatus: handleAgentStatus,
    onJobCreated: handleJobCreated,
    onJobUpdated: handleJobUpdated,
    onAgentNeed: handleAgentNeed,
    onAgentBlocker: handleAgentBlocker,
  });

  // Send message handler
  const handleSendMessage = useCallback(async (content: string, type: Message['type'] = 'text') => {
    if (!selectedAgentId) return;

    // Create optimistic message
    const optimisticMessage: Message = {
      id: Date.now(),
      message_id: `temp-${Date.now()}`,
      from_agent: REX_USER.id,
      to_agent: selectedAgentId,
      content,
      type,
      metadata: {},
      is_read: false,
      is_delivered: false,
      created_at: new Date().toISOString()
    };

    // Add to local thread immediately
    setThreads(prev => ({
      ...prev,
      [selectedAgentId]: {
        agentId: selectedAgentId,
        messages: [...(prev[selectedAgentId]?.messages || []), optimisticMessage],
        unreadCount: 0,
        lastMessageAt: new Date().toISOString()
      }
    }));

    // Send via WebSocket
    const sent = sendWsMessage(selectedAgentId, content, type);
    
    if (!sent) {
      // Fallback to REST API if WebSocket fails
      try {
        await messageApi.send({
          fromAgent: REX_USER.id,
          toAgent: selectedAgentId,
          content,
          type,
          metadata: {}
        });
      } catch (error) {
        console.error('Failed to send message:', error);
      }
    }
  }, [selectedAgentId, sendWsMessage]);

  // Select agent handler
  const handleSelectAgent = useCallback((agentId: string) => {
    setSelectedAgentId(agentId);
    // Clear unread count for this agent
    setUnreadCounts(prev => ({ ...prev, [agentId]: 0 }));
    setThreads(prev => ({
      ...prev,
      [agentId]: {
        ...(prev[agentId] || { agentId, messages: [] }),
        unreadCount: 0
      }
    }));
  }, []);

  // Request memory handler
  const handleRequestMemory = useCallback((_agentId: string) => {
    setShowMemoryPanel(true);
  }, []);

  // Request jobs handler
  const handleRequestJobs = useCallback((_agentId: string) => {
    setShowMemoryPanel(true);
  }, []);

  // Send command handler
  const handleSendCommand = useCallback((agentId: string, command: string) => {
    // Send command as a special message type
    handleSendMessage(`/${command}`, 'command');
    
    // Also send via WebSocket as a command
    sendWsMessage(agentId, command, 'command');
  }, [handleSendMessage, sendWsMessage]);

  return (
    <div className="h-screen flex flex-col bg-background text-foreground">
      <Header 
        userName={REX_USER.name}
        isConnected={isConnected}
        connectionError={connectionError}
        agentCount={agents.length}
        onlineCount={agents.filter(a => a.status === 'online').length}
        stats={serverStats || undefined}
        onRefresh={() => {
          loadAgents();
          loadStats();
        }}
      />

      <div className="flex-1 flex overflow-hidden">
        <AgentList
          agents={agents}
          selectedAgentId={selectedAgentId}
          onSelectAgent={handleSelectAgent}
          unreadCounts={unreadCounts}
          onRefresh={loadAgents}
          isLoading={isLoadingAgents}
        />

        <ChatWindow
          agent={selectedAgent}
          messages={messages}
          currentUser={REX_USER}
          onSendMessage={handleSendMessage}
          onRequestMemory={handleRequestMemory}
          onRequestJobs={handleRequestJobs}
          onSendCommand={handleSendCommand}
          isTyping={isTyping}
          isLoading={isLoadingMessages}
        />

        <AgentMemoryPanel
          agent={selectedAgent}
          isOpen={showMemoryPanel}
          onClose={() => setShowMemoryPanel(false)}
        />
      </div>

      {/* Dashboard Modal */}
      {showDashboard && (
        <Dashboard
          agents={agents}
          onSelectAgent={handleSelectAgent}
          isOpen={showDashboard}
          onClose={() => setShowDashboard(false)}
        />
      )}

      {/* Floating Dashboard Button */}
      <button
        onClick={() => setShowDashboard(true)}
        className="fixed bottom-4 right-4 p-3 bg-primary text-primary-foreground rounded-full shadow-lg hover:bg-primary/90 transition-colors z-40"
        title="Open Dashboard"
      >
        <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
        </svg>
      </button>
    </div>
  );
}

export default App;