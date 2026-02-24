import React, { useState, useRef, useEffect } from 'react';
import { Send, Loader2 } from 'lucide-react';

export function ChatWindow({ 
  selectedAgent, 
  messages, 
  currentAgentId, 
  onSendMessage, 
  onTyping,
  isTyping 
}) {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef(null);
  
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };
  
  useEffect(() => {
    scrollToBottom();
  }, [messages]);
  
  const handleSubmit = (e) => {
    e.preventDefault();
    if (input.trim() && selectedAgent) {
      onSendMessage(selectedAgent.id, input.trim());
      setInput('');
    }
  };
  
  const handleInputChange = (e) => {
    setInput(e.target.value);
    if (selectedAgent) {
      onTyping(selectedAgent.id);
    }
  };
  
  const filteredMessages = messages.filter(
    m => (m.from === currentAgentId && m.to === selectedAgent?.id) ||
         (m.from === selectedAgent?.id && m.to === currentAgentId)
  );
  
  if (!selectedAgent) {
    return (
      <div className="flex-1 flex items-center justify-center bg-gray-950">
        <div className="text-center text-gray-500">
          <p className="text-lg mb-2">Select an agent to start chatting</p>
          <p className="text-sm">Connect with your AI team members</p>
        </div>
      </div>
    );
  }
  
  return (
    <div className="flex-1 flex flex-col bg-gray-950">
      {/* Header */}
      <div className="p-4 border-b border-gray-800 flex items-center gap-3">
        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white font-semibold">
          {selectedAgent.name?.[0]?.toUpperCase() || 'A'}
        </div>
        <div>
          <div className="text-white font-semibold">{selectedAgent.name}</div>
          <div className="text-gray-400 text-sm flex items-center gap-2">
            <span>{selectedAgent.role}</span>
            <span className="text-gray-600">•</span>
            <span className={`text-sm ${
              selectedAgent.status === 'online' ? 'text-green-400' : 'text-gray-500'
            }`}>
              {selectedAgent.status}
            </span>
          </div>
        </div>
      </div>
      
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {filteredMessages.length === 0 ? (
          <div className="text-center text-gray-500 mt-8">
            No messages yet. Start the conversation!
          </div>
        ) : (
          filteredMessages.map((message) => {
            const isMe = message.from === currentAgentId;
            return (
              <div
                key={message.id}
                className={`flex ${isMe ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[70%] px-4 py-2 rounded-2xl ${
                    isMe
                      ? 'bg-blue-600 text-white rounded-br-sm'
                      : 'bg-gray-800 text-gray-100 rounded-bl-sm'
                  }`}
                >
                  <p>{message.content}</p>
                  <div className={`text-xs mt-1 ${isMe ? 'text-blue-200' : 'text-gray-500'}`}>
                    {new Date(message.timestamp).toLocaleTimeString([], { 
                      hour: '2-digit', 
                      minute: '2-digit' 
                    })}
                  </div>
                </div>
              </div>
            );
          })
        )}
        
        {isTyping && (
          <div className="flex justify-start">
            <div className="bg-gray-800 px-4 py-2 rounded-2xl rounded-bl-sm flex items-center gap-2">
              <Loader2 className="w-4 h-4 text-gray-400 animate-spin" />
              <span className="text-gray-400 text-sm">{selectedAgent.name} is typing...</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>
      
      {/* Input */}
      <form onSubmit={handleSubmit} className="p-4 border-t border-gray-800">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={handleInputChange}
            placeholder={`Message ${selectedAgent.name}...`}
            className="flex-1 bg-gray-800 text-white px-4 py-3 rounded-xl border border-gray-700 focus:outline-none focus:border-blue-500"
          />
          <button
            type="submit"
            disabled={!input.trim()}
            className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:cursor-not-allowed text-white px-4 py-3 rounded-xl transition-colors"
          >
            <Send className="w-5 h-5" />
          </button>
        </div>
      </form>
    </div>
  );
}
