import { useState, useEffect } from 'react';
import { Agent, AgentJob, AgentMemory } from '../types';
import { agentApi } from '../api';
import { 
  Brain, 
  Briefcase, 
  AlertCircle, 
  X,
  Clock,
  CheckCircle2,
  XCircle,
  Loader2,
  Lightbulb,
  HelpCircle,
  Eye,
  Target,
  AlertTriangle,
  RefreshCw,
  Filter
} from 'lucide-react';

interface AgentMemoryPanelProps {
  agent: Agent | null;
  isOpen: boolean;
  onClose: () => void;
}

export function AgentMemoryPanel({ agent, isOpen, onClose }: AgentMemoryPanelProps) {
  const [activeTab, setActiveTab] = useState<'jobs' | 'memory' | 'blockers'>('jobs');
  const [jobs, setJobs] = useState<AgentJob[]>([]);
  const [memories, setMemories] = useState<AgentMemory[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [jobFilter, setJobFilter] = useState<string | null>(null);
  const [memoryFilter, setMemoryFilter] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && agent) {
      loadData();
    }
  }, [isOpen, agent, activeTab]);

  const loadData = async () => {
    if (!agent) return;
    
    setIsLoading(true);
    setError(null);
    
    try {
      if (activeTab === 'jobs') {
        const response = await agentApi.getJobs(agent.agent_id, { limit: 50 });
        setJobs(response.jobs || []);
      } else if (activeTab === 'memory') {
        const response = await agentApi.getMemory(agent.agent_id, { limit: 50 });
        setMemories(response.memories || []);
      } else if (activeTab === 'blockers') {
        const response = await agentApi.getMemory(agent.agent_id, { 
          types: 'blocker', 
          limit: 50,
          minImportance: 1 
        });
        setMemories(response.memories || []);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data');
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen || !agent) return null;

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'in_progress':
        return <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />;
      case 'completed':
        return <CheckCircle2 className="h-4 w-4 text-green-500" />;
      case 'failed':
        return <XCircle className="h-4 w-4 text-red-500" />;
      case 'cancelled':
        return <X className="h-4 w-4 text-gray-500" />;
      default:
        return <Clock className="h-4 w-4 text-yellow-500" />;
    }
  };

  const getMemoryIcon = (type: string) => {
    switch (type) {
      case 'insight':
        return <Lightbulb className="h-4 w-4 text-yellow-500" />;
      case 'decision':
        return <CheckCircle2 className="h-4 w-4 text-green-500" />;
      case 'question':
        return <HelpCircle className="h-4 w-4 text-blue-500" />;
      case 'need':
        return <Target className="h-4 w-4 text-purple-500" />;
      case 'blocker':
        return <AlertTriangle className="h-4 w-4 text-red-500" />;
      case 'thought':
        return <Brain className="h-4 w-4 text-cyan-500" />;
      default:
        return <Eye className="h-4 w-4 text-gray-500" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'in_progress':
        return 'bg-blue-500/20 text-blue-400';
      case 'completed':
        return 'bg-green-500/20 text-green-400';
      case 'failed':
        return 'bg-red-500/20 text-red-400';
      case 'cancelled':
        return 'bg-gray-500/20 text-gray-400';
      default:
        return 'bg-yellow-500/20 text-yellow-400';
    }
  };

  const formatRelativeTime = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);
    
    if (minutes < 1) return 'just now';
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    if (days < 7) return `${days}d ago`;
    return date.toLocaleDateString();
  };

  const filteredJobs = jobFilter 
    ? jobs.filter(j => j.status === jobFilter)
    : jobs;

  const filteredMemories = memoryFilter
    ? memories.filter(m => m.memory_type === memoryFilter)
    : memories;

  const pendingJobs = jobs.filter(j => j.status === 'pending').length;
  const inProgressJobs = jobs.filter(j => j.status === 'in_progress').length;
  const completedJobs = jobs.filter(j => j.status === 'completed').length;

  return (
    <div className="w-96 bg-card border-l border-border flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-border">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Brain className="h-5 w-5 text-primary" />
            <h3 className="font-semibold">Agent Memory</h3>
          </div>
          <div className="flex items-center gap-1">
            <button
              onClick={loadData}
              disabled={isLoading}
              className="p-1.5 hover:bg-accent rounded transition-colors disabled:opacity-50"
              title="Refresh"
            >
              <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
            </button>
            <button
              onClick={onClose}
              className="p-1.5 hover:bg-accent rounded transition-colors"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>
        
        <div className="mt-3 flex items-center gap-2 p-2 bg-muted/50 rounded-lg">
          <div className="w-8 h-8 rounded bg-primary/20 flex items-center justify-center">
            <span className="text-sm font-bold text-primary">{agent.name.charAt(0)}</span>
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium truncate">{agent.name}</p>
            <p className="text-xs text-muted-foreground">{agent.type} • {agent.status}</p>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-border">
        {[
          { 
            id: 'jobs', 
            label: 'Jobs', 
            icon: Briefcase, 
            badge: pendingJobs + inProgressJobs 
          },
          { 
            id: 'memory', 
            label: 'Memory', 
            icon: Brain, 
            badge: memories.filter(m => !memoryFilter || m.memory_type === memoryFilter).length 
          },
          { 
            id: 'blockers', 
            label: 'Blockers', 
            icon: AlertTriangle, 
            badge: memories.filter(m => m.memory_type === 'blocker').length 
          },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as typeof activeTab)}
            className={`
              flex-1 flex items-center justify-center gap-1.5 py-3 text-sm
              transition-colors relative
              ${activeTab === tab.id ? 'text-primary' : 'text-muted-foreground hover:text-foreground'}
            `}
          >
            <tab.icon className="h-4 w-4" />
            <span className="hidden sm:inline">{tab.label}</span>
            {tab.badge > 0 && (
              <span className={`
                text-xs px-1.5 py-0.5 rounded-full
                ${activeTab === tab.id ? 'bg-primary text-primary-foreground' : 'bg-muted'}
              `}>
                {tab.badge}
              </span>
            )}
            {activeTab === tab.id && (
              <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary" />
            )}
          </button>
        ))}
      </div>

      {/* Filters */}
      <div className="px-4 py-2 border-b border-border bg-muted/20">
        {activeTab === 'jobs' && (
          <div className="flex items-center gap-2 overflow-x-auto">
            <Filter className="h-3 w-3 text-muted-foreground" />
            {['all', 'pending', 'in_progress', 'completed', 'failed'].map((status) => (
              <button
                key={status}
                onClick={() => setJobFilter(status === 'all' ? null : status)}
                className={`
                  px-2 py-0.5 text-xs rounded-full whitespace-nowrap
                  ${jobFilter === status || (status === 'all' && !jobFilter)
                    ? 'bg-primary text-primary-foreground' 
                    : 'bg-muted text-muted-foreground hover:text-foreground'}
                `}
              >
                {status === 'all' ? 'All' : status.replace('_', ' ')}
                {status !== 'all' && (
                  <span className="ml-1 opacity-70">({jobs.filter(j => j.status === status).length})</span>
                )}
              </button>
            ))}
          </div>
        )}
        
        {(activeTab === 'memory' || activeTab === 'blockers') && (
          <div className="flex items-center gap-2 overflow-x-auto">
            <Filter className="h-3 w-3 text-muted-foreground" />
            {['all', 'thought', 'observation', 'decision', 'need', 'blocker', 'insight'].map((type) => (
              <button
                key={type}
                onClick={() => setMemoryFilter(type === 'all' ? null : type)}
                className={`
                  px-2 py-0.5 text-xs rounded-full whitespace-nowrap
                  ${memoryFilter === type || (type === 'all' && !memoryFilter)
                    ? 'bg-primary text-primary-foreground' 
                    : 'bg-muted text-muted-foreground hover:text-foreground'}
                `}
              >
                {type === 'all' ? 'All' : type}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {error && (
          <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">
            <div className="flex items-center gap-2">
              <AlertCircle className="h-4 w-4" />
              <span>{error}</span>
            </div>
          </div>
        )}

        {isLoading ? (
          <div className="flex items-center justify-center h-32">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : activeTab === 'jobs' ? (
          <div className="space-y-3">
            {filteredJobs.length === 0 ? (
              <div className="text-center text-muted-foreground py-8">
                <Briefcase className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">No jobs found</p>
              </div>
            ) : (
              filteredJobs.map((job) => (
                <div
                  key={job.job_id}
                  className="p-3 bg-muted/50 rounded-lg border border-border hover:border-primary/30 transition-colors"
                >
                  <div className="flex items-start gap-3">
                    <div className="mt-0.5">{getStatusIcon(job.status)}</div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{job.title}</p>
                      
                      {job.description && (
                        <p className="text-xs text-muted-foreground mt-1 line-clamp-2">{job.description}</p>
                      )}
                      
                      <div className="flex items-center gap-2 mt-2">
                        <span className={`text-[10px] px-1.5 py-0.5 rounded ${getStatusColor(job.status)}`}>
                          {job.status.replace('_', ' ')}
                        </span>
                        
                        <span className="text-[10px] text-muted-foreground">
                          P{job.priority}
                        </span>
                        
                        {job.started_at && (
                          <span className="text-[10px] text-muted-foreground">
                            Started {formatRelativeTime(job.started_at)}
                          </span>
                        )}
                      </div>
                      
                      {job.result && (
                        <div className="mt-2 p-2 bg-muted rounded text-xs text-muted-foreground">
                          {job.result}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        ) : activeTab === 'memory' ? (
          <div className="space-y-3">
            {filteredMemories.length === 0 ? (
              <div className="text-center text-muted-foreground py-8">
                <Brain className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">No memories recorded</p>
              </div>
            ) : (
              filteredMemories.map((memory) => (
                <div
                  key={memory.id}
                  className="p-3 bg-muted/50 rounded-lg border border-border"
                >
                  <div className="flex items-start gap-3">
                    <div className="mt-0.5">{getMemoryIcon(memory.memory_type)}</div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-[10px] uppercase tracking-wider text-muted-foreground">
                          {memory.memory_type}
                        </span>
                        <span className="text-[10px] text-muted-foreground">
                          • {formatRelativeTime(memory.created_at || '')}
                        </span>
                      </div>
                      
                      <p className="text-sm">{memory.content}</p>
                      
                      {memory.importance >= 4 && (
                        <div className="mt-2 flex items-center gap-1">
                          <AlertTriangle className="h-3 w-3 text-yellow-500" />
                          <span className="text-[10px] text-yellow-500">High importance</span>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        ) : (
          <div className="space-y-3">
            {filteredMemories.filter(m => m.memory_type === 'blocker').length === 0 ? (
              <div className="text-center text-muted-foreground py-8">
                <CheckCircle2 className="h-8 w-8 mx-auto mb-2 text-green-500 opacity-50" />
                <p className="text-sm">No active blockers</p>
                <p className="text-xs mt-1">Agent is operating normally</p>
              </div>
            ) : (
              filteredMemories
                .filter(m => m.memory_type === 'blocker')
                .map((blocker) => (
                  <div
                    key={blocker.id}
                    className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg"
                  >
                    <div className="flex items-start gap-3">
                      <AlertTriangle className="h-4 w-4 text-red-500 mt-0.5" />
                      <div className="flex-1">
                        <p className="text-sm font-medium text-red-400">{blocker.content}</p>
                        <p className="text-xs text-muted-foreground mt-1">
                          Reported {formatRelativeTime(blocker.created_at || '')}
                        </p>
                      </div>
                    </div>
                  </div>
                ))
            )}
          </div>
        )}
      </div>

      {/* Footer Stats */}
      <div className="p-4 border-t border-border bg-muted/30">
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <div>
            <div className="font-bold text-yellow-500">{pendingJobs}</div>
            <div className="text-muted-foreground">Pending</div>
          </div>
          <div>
            <div className="font-bold text-blue-500">{inProgressJobs}</div>
            <div className="text-muted-foreground">Active</div>
          </div>
          <div>
            <div className="font-bold text-green-500">{completedJobs}</div>
            <div className="text-muted-foreground">Done</div>
          </div>
        </div>
      </div>
    </div>
  );
}