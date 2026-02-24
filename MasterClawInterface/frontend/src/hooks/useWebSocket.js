import React, { useState, useEffect } from 'react';
import { io } from 'socket.io-client';

const SOCKET_URL = process.env.REACT_APP_SOCKET_URL || 'http://localhost:3001';

export function useWebSocket(agentId, agentName, agentRole) {
  const [socket, setSocket] = useState(null);
  const [connected, setConnected] = useState(false);
  const [messages, setMessages] = useState([]);
  const [agents, setAgents] = useState([]);
  const [typing, setTyping] = useState({});
  const [error, setError] = useState(null);

  useEffect(() => {
    const newSocket = io(SOCKET_URL);
    
    newSocket.on('connect', () => {
      console.log('Connected to MasterClaw Interface');
      setConnected(true);
      setError(null);
      
      // Register as agent
      newSocket.emit('register', {
        agentId,
        name: agentName,
        role: agentRole
      });
    });
    
    newSocket.on('disconnect', () => {
      console.log('Disconnected from MasterClaw Interface');
      setConnected(false);
    });
    
    newSocket.on('connect_error', (err) => {
      console.error('Connection error:', err);
      setError('Failed to connect to server');
    });
    
    newSocket.on('message', (message) => {
      setMessages(prev => [...prev, message]);
    });
    
    newSocket.on('agent:joined', (agent) => {
      setAgents(prev => {
        const exists = prev.find(a => a.id === agent.agentId);
        if (exists) {
          return prev.map(a => a.id === agent.agentId ? { ...a, ...agent } : a);
        }
        return [...prev, { id: agent.agentId, name: agent.name, role: agent.role, status: agent.status }];
      });
    });
    
    newSocket.on('agent:status', ({ agentId, status }) => {
      setAgents(prev => prev.map(a => 
        a.id === agentId ? { ...a, status } : a
      ));
    });
    
    newSocket.on('agent:typing', ({ agentId }) => {
      setTyping(prev => ({ ...prev, [agentId]: true }));
      setTimeout(() => {
        setTyping(prev => ({ ...prev, [agentId]: false }));
      }, 3000);
    });
    
    setSocket(newSocket);
    
    return () => {
      newSocket.close();
    };
  }, [agentId, agentName, agentRole]);
  
  const sendMessage = (to, content, type = 'text') => {
    if (socket && connected) {
      socket.emit('message', { to, content, type });
      // Optimistically add to local state
      const message = {
        id: Date.now().toString(),
        from: agentId,
        to,
        content,
        type,
        timestamp: new Date().toISOString(),
        read: false
      };
      setMessages(prev => [...prev, message]);
    }
  };
  
  const sendTyping = (to) => {
    if (socket && connected) {
      socket.emit('typing', { to });
    }
  };
  
  const updateStatus = (status) => {
    if (socket && connected) {
      socket.emit('status', { status });
    }
  };
  
  return {
    socket,
    connected,
    messages,
    agents,
    typing,
    error,
    sendMessage,
    sendTyping,
    updateStatus
  };
}
