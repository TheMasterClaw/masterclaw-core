import React, { useState, useEffect, useRef } from 'react';
import io from 'socket.io-client';
import './ChatInterface.css';

const ChatInterface = ({ agentId = 'rex', agentName = 'Rex' }) => {
  const [socket, setSocket] = useState(null);
  const [connected, setConnected] = useState(false);
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [selectedAgent, setSelectedAgent] = useState('');
  const [agents, setAgents] = useState([]);
  const [typing, setTyping] = useState({});
  const [agentStatus, setAgentStatus] = useState({});
  const messagesEndRef = useRef(null);
  
  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:3001';
  
  useEffect(() => {
    // Connect to WebSocket server
    const newSocket = io(API_URL);
    setSocket(newSocket);
    
    newSocket.on('connect', () => {
      console.log('Connected to MasterClaw Chat');
      setConnected(true);
      
      // Register as agent
      newSocket.emit('register_agent', {
        agentId,
        name: agentName,
        type: 'master'
      });
    });
    
    newSocket.on('disconnect', () => {
      console.log('Disconnected from MasterClaw Chat');
      setConnected(false);
    });
    
    newSocket.on('registered', (data) => {
      console.log('Registered:', data);
      fetchAgents();
    });
    
    newSocket.on('message', (data) => {
      setMessages(prev => [...prev, { ...data, delivered: true }]);
    });
    
    newSocket.on('message_sent', (data) => {
      console.log('Message sent:', data);
    });
    
    newSocket.on('typing', (data) => {
      setTyping(prev => ({
        ...prev,
        [data.from]: data.isTyping
      }));
      
      // Clear typing indicator after 3 seconds
      if (data.isTyping) {
        setTimeout(() => {
          setTyping(prev => ({
            ...prev,
            [data.from]: false
          }));
        }, 3000);
      }
    });
    
    newSocket.on('agent_status', (data) => {
      setAgentStatus(prev => ({
        ...prev,
        [data.agentId]: data.status
      }));
    });
    
    newSocket.on('unread_messages', (data) => {
      console.log('Unread messages:', data);
      setMessages(prev => [...data.map(m => ({ ...m, delivered: true })), ...prev]);
    });
    
    newSocket.on('error', (error) => {
      console.error('Socket error:', error);
    });
    
    return () => {
      newSocket.close();
    };
  }, [agentId, agentName]);
  
  useEffect(() => {
    scrollToBottom();
  }, [messages]);
  
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };
  
  const fetchAgents = async () => {
    try {
      const response = await fetch(`${API_URL}/api/agents`);
      const data = await response.json();
      setAgents(data.agents || []);
      
      // Set initial status
      const statusMap = {};
      data.agents.forEach(agent => {
        statusMap[agent.agent_id] = agent.status;
      });
      setAgentStatus(statusMap);
    } catch (error) {
      console.error('Error fetching agents:', error);
    }
  };
  
  const handleSendMessage = (e) => {
    e.preventDefault();
    
    if (!inputMessage.trim() || !selectedAgent || !socket) return;
    
    const messageData = {
      to: selectedAgent,
      content: inputMessage,
      type: 'text'
    };
    
    socket.emit('send_message', messageData);
    
    // Add to local messages
    setMessages(prev => [...prev, {
      messageId: `local-${Date.now()}`,
      from: agentId,
      to: selectedAgent,
      content: inputMessage,
      type: 'text',
      timestamp: new Date().toISOString(),
      pending: true
    }]);
    
    setInputMessage('');
  };
  
  const handleTyping = () => {
    if (socket && selectedAgent) {
      socket.emit('typing', { to: selectedAgent, isTyping: true });
    }
  };
  
  const getStatusColor = (status) => {
    switch (status) {
      case 'online': return '#4CAF50';
      case 'busy': return '#FF9800';
      case 'away': return '#FFC107';
      default: return '#9E9E9E';
    }
  };
  
  const filteredMessages = selectedAgent 
    ? messages.filter(m => 
        (m.from === agentId && m.to === selectedAgent) || 
        (m.from === selectedAgent && m.to === agentId)
      )
    : messages;
  
  return (
    <div className="chat-interface">
      <div className="chat-sidebar">
        <div className="chat-header">
          <h2>MasterClaw Chat</h2>
          <div className={`connection-status ${connected ? 'connected' : 'disconnected'}`}>
            {connected ? '🟢 Connected' : '🔴 Disconnected'}
          </div>
        </div>
        
        <div className="agents-list">
          <h3>Agents</h3>
          {agents.map(agent => (
            <div
              key={agent.agent_id}
              className={`agent-item ${selectedAgent === agent.agent_id ? 'selected' : ''}`}
              onClick={() => setSelectedAgent(agent.agent_id)}
            >
              <div 
                className="agent-status-dot"
                style={{ backgroundColor: getStatusColor(agentStatus[agent.agent_id]) }}
              />
              <div className="agent-info">
                <div className="agent-name">{agent.name}</div>
                <div className="agent-type">{agent.type}</div>
              </div>
              {typing[agent.agent_id] && (
                <span className="typing-indicator">typing...</span>
              )}
            </div>
          ))}
        </div>
      </div>
      
      <div className="chat-main">
        {selectedAgent ? (
          <>
            <div className="chat-messages">
              {filteredMessages.map((msg, index) => (
                <div
                  key={msg.messageId || index}
                  className={`message ${msg.from === agentId ? 'sent' : 'received'}`}
                >
                  <div className="message-content">{msg.content}</div>
                  <div className="message-meta">
                    <span className="message-time">
                      {new Date(msg.timestamp).toLocaleTimeString()}
                    </span>
                    {msg.from === agentId && (
                      <span className="message-status">
                        {msg.pending ? '⏳' : '✓'}
                      </span>
                    )}
                  </div>
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>
            
            <form className="chat-input" onSubmit={handleSendMessage}>
              <input
                type="text"
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyPress={handleTyping}
                placeholder={`Message ${selectedAgent}...`}
                disabled={!connected}
              />
              <button type="submit" disabled={!connected || !inputMessage.trim()}>
                Send
              </button>
            </form>
          </>
        ) : (
          <div className="no-chat-selected">
            <p>Select an agent to start chatting</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default ChatInterface;
