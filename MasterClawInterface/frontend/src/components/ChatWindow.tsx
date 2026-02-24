import { useRef, useEffect, useState } from 'react';
import { Message, Agent, User } from '../types';
import { 
  Send, 
  Bot, 
  User as UserIcon, 
  Brain,
  Command,
  Sparkles,
  Paperclip,
  MoreVertical
} from 'lucide-react';

interface ChatWindowProps {
  agent: Agent | null;
  messages: Message[];
  currentUser: User;
  onSendMessage: (content: string, type?: Message['type']) => void;
  onRequestMemory?: (agentId: string) => void;
  onRequestJobs?: (agentId: string) => void;
  onSendCommand?: (agentId: string, command: string) => void;
  isTyping?: boolean;
  isLoading?: boolean;
}

export function ChatWindow({ 
  agent, 
  messages, 
  currentUser, 
  onSendMessage,
  onRequestMemory,
  onRequestJobs,
  onSendCommand,
  isTyping = false,
  isLoading = false
}: ChatWindowProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const [inputValue, setInputValue] = useState('');

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  // Auto-resize textarea
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = 'auto';
      inputRef.current.style.height = `${Math.min(inputRef.current.scrollHeight, 120)}px`;
    }
  }, [inputValue]);

  const handleSend = () => {
    if (!inputValue.trim() || !agent) return;
    
    // Check for command prefix
    if (inputValue.startsWith('/')) {
      const command = inputValue.slice(1).trim();
      onSendCommand?.(agent.agent_id, command);
    } else {
      onSendMessage(inputValue, 'text');
    }
    setInputValue('');
    if (inputRef.current) {
      inputRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const formatTime = (dateStr: string) => {
    return new Date(dateStr).toLocaleTimeString([], { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);

    if (date.toDateString() === today.toDateString()) {
      return 'Today';
    } else if (date.toDateString() === yesterday.toDateString()) {
      return 'Yesterday';
    } else {
      return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
    }
  };

  const getMessageIcon = (type: Message['type']) => {
    switch (type) {
      case 'thought':
        return <Brain className="h-3 w-3" />;
      case 'command':
        return <Command className="h-3 w-3" />;
      case 'system':
        return <Sparkles className="h-3 w-3" />;
      default:
        return null;
    }
  };

  const quickCommands = [
    { label: 'Status', command: 'status', description: 'Get agent status' },
    { label: 'Memory', command: 'memory', description: 'View recent thoughts' },
    { label: 'Jobs', command: 'jobs', description: 'List active jobs' },
    { label: 'Pause', command: 'pause', description: 'Pause current task' },
    { label: 'Resume', command: 'resume', description: 'Resume paused task' },
    { label: 'Help', command: 'help', description: 'Show available commands' },
  ];

  // Group messages by date
  const groupedMessages = messages.reduce((groups, message) => {
    const date = new Date(message.created_at).toDateString();
    if (!groups[date]) {
      groups[date] = [];
    }
    groups[date].push(message);
    return groups;
  }, {} as Record<string, Message[]>);

  if (!agent) {
    return (
      <div className="flex-1 flex items-center justify-center bg-card">
        <div className="text-center p-8">
          <div className="w-20 h-20 bg-muted rounded-full flex items-center justify-center mx-auto mb-4">
            <Bot className="h-10 w-10 text-muted-foreground" />
          </div>
          <h3 className="text-xl font-semibold mb-2">Welcome to MasterClaw</h3>
          <p className="text-muted-foreground max-w-sm">
            Select an agent from the sidebar to start a conversation. 
            You can send messages, commands, and view agent memory.
          </p>
          <div className="mt-6 flex gap-2 justify-center">
            <div className="px-3 py-1.5 bg-muted rounded-lg text-sm text-muted-foreground">
              /status - Check agent status
            </div>
            <div className="px-3 py-1.5 bg-muted rounded-lg text-sm text-muted-foreground">
              /help - Show commands
            </div>
          </div>
        </div>
      </div>
    );
  }

  const statusColors = {
    online: 'bg-green-500',
    offline: 'bg-gray-500',
    busy: 'bg-yellow-500',
    error: 'bg-red-500',
    away: 'bg-orange-500',
  };

  return (
    <div className="flex-1 flex flex-col bg-card h-full">
      {/* Header */}
      <div className="p-4 border-b border-border flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className={`
            p-2 rounded-lg
            ${agent.status === 'online' ? 'bg-green-500/20' : ''}
            ${agent.status === 'busy' ? 'bg-yellow-500/20' : ''}
            ${agent.status === 'offline' ? 'bg-gray-500/20' : ''}
            ${agent.status === 'error' ? 'bg-red-500/20' : ''}
            ${agent.status === 'away' ? 'bg-orange-500/20' : ''}
          `}>
            <Bot className="h-5 w-5" />
          </div>
          
          <div>
            <h3 className="font-semibold">{agent.name}</h3>
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <span className="flex items-center gap-1">
                <span className={`h-2 w-2 rounded-full ${statusColors[agent.status]}`} />
                {agent.status}
              </span>
              {agent.type && <span>• {agent.type}</span>}
              {agent.current_job && (
                <span className="text-primary truncate max-w-[200px]">• {agent.current_job}</span>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => onRequestMemory?.(agent.agent_id)}
            className="flex items-center gap-1.5 px-3 py-1.5 hover:bg-accent rounded-lg transition-colors text-sm"
            title="View Agent Memory"
          >
            <Brain className="h-4 w-4" />
            <span className="hidden sm:inline">Memory</span>
          </button>
          <button
            onClick={() => onRequestJobs?.(agent.agent_id)}
            className="flex items-center gap-1.5 px-3 py-1.5 hover:bg-accent rounded-lg transition-colors text-sm"
            title="View Jobs"
          >
            <Command className="h-4 w-4" />
            <span className="hidden sm:inline">Jobs</span>
          </button>
          <div className="h-6 w-px bg-border mx-1" />
          <button className="p-2 hover:bg-accent rounded-lg transition-colors">
            <MoreVertical className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Quick Commands Bar */}
      <div className="px-4 py-2 border-b border-border bg-muted/20">
        <div className="flex items-center gap-2 overflow-x-auto">
          <span className="text-xs text-muted-foreground whitespace-nowrap">Quick commands:</span>
          {quickCommands.map((cmd) => (
            <button
              key={cmd.command}
              onClick={() => onSendCommand?.(agent.agent_id, cmd.command)}
              className="px-2.5 py-1 text-xs bg-accent hover:bg-accent/80 rounded-full transition-colors whitespace-nowrap"
              title={cmd.description}
            >
              /{cmd.command}
            </button>
          ))}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        {isLoading ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center text-muted-foreground">
              <div className="animate-spin h-8 w-8 border-2 border-primary border-t-transparent rounded-full mx-auto mb-3" />
              <p>Loading messages...</p>
            </div>
          </div>
        ) : messages.length === 0 ? (
          <div className="text-center text-muted-foreground py-8">
            <div className="w-16 h-16 bg-muted rounded-full flex items-center justify-center mx-auto mb-4">
              <Bot className="h-8 w-8 opacity-50" />
            </div>
            <p>No messages yet</p>
            <p className="text-sm mt-1">Start the conversation with {agent.name}</p>
          </div>
        ) : (
          Object.entries(groupedMessages).map(([date, dateMessages]) => (
            <div key={date}>
              {/* Date separator */}
              <div className="flex items-center justify-center my-4">
                <div className="bg-muted px-3 py-1 rounded-full text-xs text-muted-foreground">
                  {formatDate(dateMessages[0].created_at)}
                </div>
              </div>

              {/* Messages for this date */}
              <div className="space-y-4">
                {dateMessages.map((message, index) => {
                  const isMe = message.from_agent === currentUser.id;
                  const showAvatar = index === 0 || dateMessages[index - 1].from_agent !== message.from_agent;

                  return (
                    <div
                      key={message.message_id || message.id}
                      className={`flex gap-3 ${isMe ? 'flex-row-reverse' : ''} animate-slide-in`}
                    >
                      {/* Avatar */}
                      {showAvatar ? (
                        <div className={`
                          w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0
                          ${isMe ? 'bg-primary' : 'bg-muted'}
                        `}>
                          {isMe ? (
                            <UserIcon className="h-4 w-4" />
                          ) : (
                            <Bot className="h-4 w-4" />
                          )}
                        </div>
                      ) : (
                        <div className="w-8 flex-shrink-0" />
                      )}

                      {/* Message Content */}
                      <div className={`max-w-[70%] ${isMe ? 'items-end' : 'items-start'} flex flex-col`}>
                        {showAvatar && (
                          <span className="text-xs text-muted-foreground mb-1">
                            {isMe ? currentUser.name : agent.name}
                          </span>
                        )}
                        
                        <div
                          className={`
                            px-4 py-2 rounded-2xl
                            ${isMe 
                              ? 'bg-primary text-primary-foreground rounded-br-none' 
                              : 'bg-muted rounded-bl-none'}
                            ${message.type === 'thought' ? 'border border-yellow-500/30' : ''}
                            ${message.type === 'command' ? 'border border-blue-500/30' : ''}
                            ${message.type === 'system' ? 'border border-purple-500/30 italic' : ''}
                          `}
                        >
                          {message.type !== 'text' && (
                            <div className="flex items-center gap-2 mb-1 opacity-70">
                              {getMessageIcon(message.type)}
                              <span className="text-[10px] uppercase tracking-wider">{message.type}</span>
                            </div>
                          )}
                          <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                        </div>
                        
                        <span className="text-[10px] text-muted-foreground mt-1">
                          {formatTime(message.created_at)}
                          {message.is_read && isMe && <span className="ml-1">✓✓</span>}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ))
        )}

        {/* Typing Indicator */}
        {isTyping && (
          <div className="flex gap-3 animate-slide-in">
            <div className="w-8 h-8 rounded-full bg-muted flex items-center justify-center">
              <Bot className="h-4 w-4" />
            </div>
            <div className="bg-muted px-4 py-3 rounded-2xl rounded-bl-none">
              <div className="flex gap-1">
                <span className="w-2 h-2 bg-muted-foreground rounded-full typing-dot" />
                <span className="w-2 h-2 bg-muted-foreground rounded-full typing-dot" />
                <span className="w-2 h-2 bg-muted-foreground rounded-full typing-dot" />
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-4 border-t border-border">
        <div className="flex items-end gap-2">
          <button className="p-3 hover:bg-accent rounded-lg transition-colors text-muted-foreground">
            <Paperclip className="h-5 w-5" />
          </button>
          
          <div className="flex-1 relative">
            <textarea
              ref={inputRef}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={`Message ${agent.name}... (use / for commands)`}
              rows={1}
              className="w-full px-4 py-3 bg-muted rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-primary text-sm min-h-[44px]"
              disabled={agent.status === 'offline'}
            />
          </div>
          
          <button
            onClick={handleSend}
            disabled={!inputValue.trim() || agent.status === 'offline'}
            className="p-3 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Send className="h-5 w-5" />
          </button>
        </div>
        
        <p className="text-[10px] text-muted-foreground mt-2">
          Press Enter to send, Shift+Enter for new line • Use /command for agent commands
        </p>
      </div>
    </div>
  );
}