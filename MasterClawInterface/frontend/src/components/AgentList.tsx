import { useState } from 'react';
import { Agent } from '../types';
import { 
  Bot, 
  Circle, 
  Cpu,
  RefreshCw,
  Search
} from 'lucide-react';

interface AgentListProps {
  agents: Agent[];
  selectedAgentId: string | null;
  onSelectAgent: (agentId: string) => void;
  unreadCounts: Record<string, number>;
  onRefresh?: () => void;
  isLoading?: boolean;
}

const statusColors = {
  online: 'text-green-500',
  offline: 'text-gray-500',
  busy: 'text-yellow-500',
  error: 'text-red-500',
  away: 'text-orange-500',
};

const statusBgColors = {
  online: 'bg-green-500/20',
  offline: 'bg-gray-500/20',
  busy: 'bg-yellow-500/20',
  error: 'bg-red-500/20',
  away: 'bg-orange-500/20',
};

export function AgentList({ 
  agents, 
  selectedAgentId, 
  onSelectAgent,
  unreadCounts,
  onRefresh,
  isLoading = false
}: AgentListProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [filterStatus, setFilterStatus] = useState<string | null>(null);

  const filteredAgents = agents.filter(agent => {
    const matchesSearch = agent.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         agent.agent_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         agent.type.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = filterStatus ? agent.status === filterStatus : true;
    return matchesSearch && matchesStatus;
  });

  const getAgentIcon = (type: string) => {
    switch (type.toLowerCase()) {
      case 'worker':
        return <Cpu className="h-4 w-4" />;
      case 'coordinator':
      case 'subagent':
        return <Bot className="h-4 w-4" />;
      default:
        return <Bot className="h-4 w-4" />;
    }
  };

  const statusCounts = {
    online: agents.filter(a => a.status === 'online').length,
    busy: agents.filter(a => a.status === 'busy').length,
    offline: agents.filter(a => a.status === 'offline').length,
    error: agents.filter(a => a.status === 'error').length,
    away: agents.filter(a => a.status === 'away').length,
  };

  return (
    <div className="flex flex-col h-full bg-card border-r border-border w-72">
      {/* Header */}
      <div className="p-4 border-b border-border">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <Bot className="h-5 w-5 text-primary" />
            Agents
          </h2>
          <button
            onClick={onRefresh}
            disabled={isLoading}
            className="p-1.5 hover:bg-accent rounded-lg transition-colors disabled:opacity-50"
            title="Refresh agents"
          >
            <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>

        {/* Search */}
        <div className="relative">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search agents..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-2 bg-muted rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary"
          />
        </div>

        {/* Status Filters */}
        <div className="flex flex-wrap gap-1.5 mt-3">
          {[
            { key: null, label: 'All', count: agents.length },
            { key: 'online', label: 'Online', count: statusCounts.online },
            { key: 'busy', label: 'Busy', count: statusCounts.busy },
            { key: 'error', label: 'Error', count: statusCounts.error },
          ].map(({ key, label, count }) => (
            <button
              key={label}
              onClick={() => setFilterStatus(key)}
              className={`
                px-2 py-1 text-xs rounded-full transition-colors
                ${filterStatus === key 
                  ? 'bg-primary text-primary-foreground' 
                  : 'bg-muted text-muted-foreground hover:text-foreground'}
              `}
            >
              {label} ({count})
            </button>
          ))}
        </div>
      </div>

      {/* Agent List */}
      <div className="flex-1 overflow-y-auto">
        {filteredAgents.length === 0 ? (
          <div className="p-8 text-center text-muted-foreground">
            <Bot className="h-12 w-12 mx-auto mb-3 opacity-50" />
            <p>No agents found</p>
            <p className="text-xs mt-1">{searchQuery ? 'Try adjusting your search' : 'Waiting for agents to register...'}</p>
          </div>
        ) : (
          <div className="divide-y divide-border">
            {filteredAgents.map((agent) => {
              const unreadCount = unreadCounts[agent.agent_id] || 0;
              const isSelected = selectedAgentId === agent.agent_id;

              return (
                <button
                  key={agent.agent_id}
                  onClick={() => onSelectAgent(agent.agent_id)}
                  className={`
                    w-full p-3 flex items-start gap-3 transition-colors text-left
                    hover:bg-accent/50
                    ${isSelected ? 'bg-accent border-l-2 border-l-primary' : 'border-l-2 border-l-transparent'}
                  `}
                >
                  {/* Avatar / Icon */}
                  <div className={`
                    relative p-2 rounded-lg
                    ${statusBgColors[agent.status]}
                  `}>
                    {getAgentIcon(agent.type)}
                    <span className={`
                      absolute -bottom-0.5 -right-0.5 h-3 w-3 rounded-full border-2 border-card
                      ${statusColors[agent.status].replace('text-', 'bg-')}
                    `} />
                  </div>

                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <span className="font-medium truncate">{agent.name}</span>
                      {unreadCount > 0 && (
                        <span className="bg-primary text-primary-foreground text-xs px-2 py-0.5 rounded-full min-w-[1.5rem] text-center">
                          {unreadCount}
                        </span>
                      )}
                    </div>
                    
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                      <span className="flex items-center gap-1">
                        <Circle className={`h-2 w-2 ${statusColors[agent.status]}`} />
                        {agent.status}
                      </span>
                      {agent.current_job && (
                        <span className="truncate max-w-[120px]">
                          • {agent.current_job}
                        </span>
                      )}
                    </div>

                    {agent.capabilities && agent.capabilities.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-1">
                        {agent.capabilities.slice(0, 2).map((cap) => (
                          <span 
                            key={cap} 
                            className="text-[10px] bg-muted px-1.5 py-0.5 rounded text-muted-foreground"
                          >
                            {cap}
                          </span>
                        ))}
                        {agent.capabilities.length > 2 && (
                          <span className="text-[10px] text-muted-foreground">
                            +{agent.capabilities.length - 2}
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* Footer Stats */}
      <div className="p-3 border-t border-border bg-muted/30">
        <div className="grid grid-cols-3 gap-2 text-center">
          <div>
            <div className="text-lg font-bold text-primary">{statusCounts.online}</div>
            <div className="text-[10px] text-muted-foreground">Online</div>
          </div>
          <div>
            <div className="text-lg font-bold text-yellow-500">{statusCounts.busy}</div>
            <div className="text-[10px] text-muted-foreground">Busy</div>
          </div>
          <div>
            <div className="text-lg font-bold text-red-500">{statusCounts.error}</div>
            <div className="text-[10px] text-muted-foreground">Errors</div>
          </div>
        </div>
      </div>
    </div>
  );
}