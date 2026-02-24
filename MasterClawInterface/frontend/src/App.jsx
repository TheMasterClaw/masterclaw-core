import { useState, useEffect, useRef } from 'react'
import { io } from 'socket.io-client'
import { 
  Send, 
  Users, 
  Brain, 
  Briefcase, 
  AlertCircle, 
  MessageSquare,
  Wifi,
  WifiOff,
  Bot,
  User
} from 'lucide-react'
import './index.css'

function App() {
  const [socket, setSocket] = useState(null)
  const [connected, setConnected] = useState(false)
  const [registered, setRegistered] = useState(false)
  const [agents, setAgents] = useState([])
  const [selectedAgent, setSelectedAgent] = useState(null)
  const [messages, setMessages] = useState([])
  const [inputMessage, setInputMessage] = useState('')
  const [activeTab, setActiveTab] = useState('chat')
  const [memory, setMemory] = useState({ thoughts: [], jobs: [], needs: [] })
  const messagesEndRef = useRef(null)

  // Initialize Socket Connection
  useEffect(() => {
    const newSocket = io('http://localhost:3001')
    setSocket(newSocket)

    newSocket.on('connect', () => {
      console.log('Connected to MasterClaw server')
      setConnected(true)
      // Register as Rex
      newSocket.emit('register-rex')
    })

    newSocket.on('disconnect', () => {
      setConnected(false)
      setRegistered(false)
    })

    newSocket.on('registered', (data) => {
      setRegistered(true)
      setAgents(data.agents)
    })

    newSocket.on('message', (message) => {
      setMessages(prev => [...prev, message])
    })

    newSocket.on('agent-status', ({ agentId, status }) => {
      setAgents(prev => prev.map(a => 
        a.id === agentId ? { ...a, online: status === 'online' } : a
      ))
    })

    return () => newSocket.close()
  }, [])

  // Auto-scroll messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Load memory when agent selected
  useEffect(() => {
    if (selectedAgent && socket) {
      socket.emit('get-memory', selectedAgent.id, (mem) => {
        setMemory(mem)
      })
    }
  }, [selectedAgent, socket])

  const sendMessage = () => {
    if (!inputMessage.trim() || !selectedAgent || !socket) return

    socket.emit('send-message', {
      to: selectedAgent.id,
      content: inputMessage,
      metadata: { priority: 'normal' }
    })

    // Add to local messages immediately
    setMessages(prev => [...prev, {
      id: Date.now(),
      from: 'rex',
      to: selectedAgent.id,
      content: inputMessage,
      timestamp: new Date().toISOString()
    }])

    setInputMessage('')
  }

  const broadcastToAll = () => {
    if (!inputMessage.trim() || !socket) return
    
    socket.emit('broadcast', { content: inputMessage })
    
    setMessages(prev => [...prev, {
      id: Date.now(),
      from: 'rex',
      to: 'all-agents',
      content: `[BROADCAST] ${inputMessage}`,
      timestamp: new Date().toISOString()
    }])
    
    setInputMessage('')
  }

  const getAgentIcon = (role) => {
    switch(role) {
      case 'research': return '🔬'
      case 'coding': return '💻'
      case 'devops': return '🚀'
      case 'security': return '🔒'
      case 'qa': return '🧪'
      case 'content': return '✍️'
      case 'orchestrator': return '🎯'
      default: return '🤖'
    }
  }

  if (!registered) {
    return (
      <div className="loading-screen">
        <div className="loading-content">
          <Bot size={64} className="animate-pulse" />
          <h1>MasterClaw Interface</h1>
          <p>{connected ? 'Registering as Rex...' : 'Connecting to server...'}</p>
          <div className={`status-dot ${connected ? 'online' : 'offline'}`} />
        </div>
      </div>
    )
  }

  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <div className="header-left">
          <Bot className="logo" />
          <h1>MasterClaw Chat</h1>
          <span className={`connection-badge ${connected ? 'online' : 'offline'}`}>
            {connected ? <Wifi size={14} /> : <WifiOff size={14} />}
            {connected ? 'Connected' : 'Disconnected'}
          </span>
        </div>
        <div className="header-right">
          <div className="rex-badge">
            <User size={16} />
            <span>Rex Deus</span>
          </div>
        </div>
      </header>

      <div className="main-container">
        {/* Sidebar - Agent List */}
        <aside className="sidebar">
          <div className="sidebar-header">
            <Users size={18} />
            <h2>Agent Fleet</h2>
          </div>
          
          <div className="agent-list">
            {agents.map(agent => (
              <button
                key={agent.id}
                className={`agent-card ${selectedAgent?.id === agent.id ? 'selected' : ''} ${agent.online ? 'online' : ''}`}
                onClick={() => setSelectedAgent(agent)}
              >
                <span className="agent-icon">{getAgentIcon(agent.role)}</span>
                <div className="agent-info">
                  <span className="agent-name">{agent.name}</span>
                  <span className="agent-role">{agent.role}</span>
                </div>
                <span className={`agent-status ${agent.online ? 'online' : 'offline'}`} />
              </button>
            ))}
          </div>
        </aside>

        {/* Main Content */}
        <main className="main">
          {selectedAgent ? (
            <>
              {/* Tabs */}
              <div className="tabs">
                <button 
                  className={activeTab === 'chat' ? 'active' : ''}
                  onClick={() => setActiveTab('chat')}
                >
                  <MessageSquare size={16} /> Chat
                </button>
                <button 
                  className={activeTab === 'memory' ? 'active' : ''}
                  onClick={() => setActiveTab('memory')}
                >
                  <Brain size={16} /> Memory
                </button>
                <button 
                  className={activeTab === 'jobs' ? 'active' : ''}
                  onClick={() => setActiveTab('jobs')}
                >
                  <Briefcase size={16} /> Jobs
                </button>
                <button 
                  className={activeTab === 'needs' ? 'active' : ''}
                  onClick={() => setActiveTab('needs')}
                >
                  <AlertCircle size={16} /> Needs
                </button>
              </div>

              {/* Chat Tab */}
              {activeTab === 'chat' && (
                <>
                  <div className="chat-header">
                    <span className="chat-agent-icon">{getAgentIcon(selectedAgent.role)}</span>
                    <div>
                      <h3>{selectedAgent.name}</h3>
                      <span className="chat-capabilities">
                        {selectedAgent.capabilities?.join(', ')}
                      </span>
                    </div>
                  </div>

                  <div className="messages-container">
                    {messages
                      .filter(m => 
                        (m.from === 'rex' && m.to === selectedAgent.id) ||
                        (m.from === selectedAgent.id && m.to === 'rex')
                      )
                      .map(message => (
                        <div 
                          key={message.id} 
                          className={`message ${message.from === 'rex' ? 'sent' : 'received'}`}
                        >
                          <div className="message-content">
                            {message.content}
                          </div>
                          <div className="message-meta">
                            {new Date(message.timestamp).toLocaleTimeString()}
                          </div>
                        </div>
                      ))
                    }
                    <div ref={messagesEndRef} />
                  </div>

                  <div className="input-container">
                    <input
                      type="text"
                      value={inputMessage}
                      onChange={(e) => setInputMessage(e.target.value)}
                      onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
                      placeholder={`Message ${selectedAgent.name}...`}
                      className="message-input"
                    />
                    <button onClick={sendMessage} className="send-btn">
                      <Send size={18} />
                    </button>
                    
                    <button onClick={broadcastToAll} className="broadcast-btn" title="Broadcast to all">
                      ALL
                    </button>
                  </div>
                </>
              )}

              {/* Memory Tab */}
              {activeTab === 'memory' && (
                <div className="memory-panel">
                  <h3>Agent Thoughts & Logs</h3>
                  <div className="memory-list">
                    {memory.thoughts?.length === 0 ? (
                      <p className="empty-state">No thoughts logged yet</p>
                    ) : (
                      memory.thoughts?.slice().reverse().map(thought => (
                        <div key={thought.id} className="memory-item">
                          <div className="memory-content">{thought.content}</div>
                          <div className="memory-time">
                            {new Date(thought.timestamp).toLocaleString()}
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              )}

              {/* Jobs Tab */}
              {activeTab === 'jobs' && (
                <div className="memory-panel">
                  <h3>Active Jobs</h3>
                  <div className="memory-list">
                    {memory.jobs?.length === 0 ? (
                      <p className="empty-state">No jobs assigned</p>
                    ) : (
                      memory.jobs?.slice().reverse().map(job => (
                        <div key={job.id} className={`memory-item job-${job.status}`}>
                          <div className="job-header">
                            <span className={`job-status-badge ${job.status}`}>{job.status}</span>
                            <span className="job-time">{new Date(job.timestamp).toLocaleString()}</span>
                          </div>
                          <div className="memory-content">{job.title || job.content}</div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              )}

              {/* Needs Tab */}
              {activeTab === 'needs' && (
                <div className="memory-panel">
                  <h3>Agent Needs</h3>
                  <div className="memory-list">
                    {memory.needs?.length === 0 ? (
                      <p className="empty-state">No needs logged</p>
                    ) : (
                      memory.needs?.slice().reverse().map(need => (
                        <div key={need.id} className={`memory-item ${need.resolved ? 'resolved' : 'unresolved'}`}>
                          <div className="need-status">{need.resolved ? '✓ Resolved' : '⚠ Open'}</div>
                          <div className="memory-content">{need.content}</div>
                          <div className="memory-time">
                            {new Date(need.timestamp).toLocaleString()}
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="no-selection">
              <Bot size={64} className="no-selection-icon" />
              <h2>Select an Agent</h2>
              <p>Choose an agent from the sidebar to start communicating</p>
            </div>
          )}
        </main>
      </div>
    </div>
  )
}

export default App
