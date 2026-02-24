import React from 'react';
import { Users, Circle } from 'lucide-react';

export function AgentList({ agents, selectedAgent, onSelectAgent, currentAgentId }) {
  const getStatusColor = (status) => {
    switch (status) {
      case 'online': return 'bg-green-500';
      case 'busy': return 'bg-yellow-500';
      case 'away': return 'bg-orange-500';
      case 'offline': return 'bg-gray-500';
      default: return 'bg-gray-500';
    }
  };
  
  const otherAgents = agents.filter(a => a.id !== currentAgentId);
  
  return (
    <div className="w-64 bg-gray-900 border-r border-gray-800 flex flex-col">
      <div className="p-4 border-b border-gray-800">
        <div className="flex items-center gap-2 text-white font-semibold">
          <Users className="w-5 h-5" />
          <span>Agents ({otherAgents.length})</span>
        </div>
      </div>
      
      <div className="flex-1 overflow-y-auto">
        {otherAgents.length === 0 ? (
          <div className="p-4 text-gray-500 text-sm text-center">
            No other agents online
          </div>
        ) : (
          otherAgents.map(agent => (
            <button
              key={agent.id}
              onClick={() => onSelectAgent(agent)}
              className={`w-full p-4 flex items-center gap-3 hover:bg-gray-800 transition-colors text-left ${
                selectedAgent?.id === agent.id ? 'bg-gray-800 border-l-2 border-blue-500' : ''
              }`}
            >
              <div className="relative">
                <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white font-semibold">
                  {agent.name?.[0]?.toUpperCase() || 'A'}
                </div>
                <Circle 
                  className={`w-3 h-3 absolute -bottom-0.5 -right-0.5 ${getStatusColor(agent.status)} rounded-full border-2 border-gray-900`}
                  fill="currentColor"
                />
              </div>
              
              <div className="flex-1 min-w-0">
                <div className="text-white font-medium truncate">
                  {agent.name}
                </div>
                <div className="text-gray-400 text-sm truncate">
                  {agent.role}
                </div>
              </div>
            </button>
          ))
        )}
      </div>
    </div>
  );
}
