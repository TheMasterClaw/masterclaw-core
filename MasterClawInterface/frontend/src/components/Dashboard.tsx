import { useState, useEffect } from 'react';
import { Agent, AgentJob, ServerStats } from '../types';
import { agentApi, statsApi } from '../api';
import { 
  Bot, 
  Activity, 
  CheckCircle2, 
  Clock, 
  AlertTriangle,
  Users,
  Cpu,
  RefreshCw,
  Zap,
  BarChart3,
  ArrowUpRight,
  ArrowDownRight
} from 'lucide-react';

interface DashboardProps {
  agents: Agent[];
  onSelectAgent: (agentId: string) => void;
  isOpen: boolean;
  onClose: () => void;
}

export function Dashboard({ agents, onSelectAgent, isOpen, onClose }: DashboardProps) {
  const [stats, setStats] = useState<ServerStats | null>(null);
  const [recentJobs, setRecentJobs] = useState<AgentJob[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      loadDashboardData();
    }
  }, [isOpen]);

  const loadDashboardData = async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const [statsRes, jobsRes] = await Promise.all([
        statsApi.getStats(),
        Promise.all(
          agents.slice(0, 5).map(agent => 
            agentApi.getJobs(agent.agent_id, { limit: 5 })
              .catch(() => ({ jobs: [] }))
          )
        )
      ]);
      
      setStats(statsRes);
      
      // Flatten and sort all jobs
      const allJobs = jobsRes.flatMap(r => r.jobs || []);
      allJobs.sort((a, b) => 
        new Date(b.created_at || '').getTime() - new Date(a.created_at || '').getTime()
      );
      setRecentJobs(allJobs.slice(0, 10));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load dashboard');
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen) return null;

  const statusCounts = {
    online: agents.filter(a => a.status === 'online').length,
    busy: agents.filter(a => a.status === 'busy').length,
    offline: agents.filter(a => a.status === 'offline').length,
    error: agents.filter(a => a.status === 'error').length,
    away: agents.filter(a => a.status === 'away').length,
  };

  const getTrendIcon = (value: number, threshold: number = 0) => {
    if (value > threshold) {
      return <ArrowUpRight className="h-4 w-4 text-green-500" />;
    } else if (value < threshold) {
      return <ArrowDownRight className="h-4 w-4 text-red-500" />;
    }
    return null;
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="w-full max-w-4xl max-h-[90vh] bg-card rounded-xl border border-border shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="p-6 border-b border-border flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-primary/20 rounded-lg flex items-center justify-center">
              <BarChart3 className="h-5 w-5 text-primary" />
            </div>
            <div>
              <h2 className="text-xl font-bold">Dashboard</h2>
              <p className="text-sm text-muted-foreground">System overview and agent activity</p>
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            <button
              onClick={loadDashboardData}
              disabled={isLoading}
              className="flex items-center gap-2 px-3 py-2 hover:bg-accent rounded-lg transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
              <span className="text-sm">Refresh</span>
            </button>
            <button
              onClick={onClose}
              className="p-2 hover:bg-accent rounded-lg transition-colors"
            >
              <span className="sr-only">Close</span>
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[calc(90vh-100px)]">
          {error && (
            <div className="mb-6 p-4 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400">
              {error}
            </div>
          )}

          {/* Stats Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            <div className="p-4 bg-muted/50 rounded-xl border border-border">
              <div className="flex items-center justify-between mb-2">
                <Users className="h-5 w-5 text-muted-foreground" />
                {getTrendIcon(statusCounts.online, agents.length / 2)}
              </div>
              <div className="text-2xl font-bold">{agents.length}</div>
              <div className="text-sm text-muted-foreground">Total Agents</div>
            </div>

            <div className="p-4 bg-muted/50 rounded-xl border border-border">
              <div className="flex items-center justify-between mb-2">
                <Activity className="h-5 w-5 text-green-500" />
              </div>
              <div className="text-2xl font-bold text-green-500">{statusCounts.online}</div>
              <div className="text-sm text-muted-foreground">Online</div>
            </div>

            <div className="p-4 bg-muted/50 rounded-xl border border-border">
              <div className="flex items-center justify-between mb-2">
                <Clock className="h-5 w-5 text-yellow-500" />
              </div>
              <div className="text-2xl font-bold text-yellow-500">{stats?.jobs.pending || 0}</div>
              <div className="text-sm text-muted-foreground">Pending Jobs</div>
            </div>

            <div className="p-4 bg-muted/50 rounded-xl border border-border">
              <div className="flex items-center justify-between mb-2">
                <Zap className="h-5 w-5 text-blue-500" />
              </div>
              <div className="text-2xl font-bold text-blue-500">{stats?.jobs.inProgress || 0}</div>
              <div className="text-sm text-muted-foreground">Active Jobs</div>
            </div>
          </div>

          <div className="grid md:grid-cols-2 gap-6">
            {/* Agent Status Distribution */}
            <div className="space-y-4">
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <Bot className="h-5 w-5" />
                Agent Status
              </h3>
              
              <div className="space-y-3">
                {[
                  { label: 'Online', count: statusCounts.online, color: 'bg-green-500', textColor: 'text-green-500' },
                  { label: 'Busy', count: statusCounts.busy, color: 'bg-yellow-500', textColor: 'text-yellow-500' },
                  { label: 'Offline', count: statusCounts.offline, color: 'bg-gray-500', textColor: 'text-gray-500' },
                  { label: 'Error', count: statusCounts.error, color: 'bg-red-500', textColor: 'text-red-500' },
                  { label: 'Away', count: statusCounts.away, color: 'bg-orange-500', textColor: 'text-orange-500' },
                ].map(({ label, count, color, textColor }) => {
                  const percentage = agents.length > 0 ? (count / agents.length) * 100 : 0;
                  return (
                    <div key={label} className="space-y-1">
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-muted-foreground">{label}</span>
                        <span className={`font-medium ${textColor}`}>{count} ({percentage.toFixed(0)}%)</span>
                      </div>
                      <div className="h-2 bg-muted rounded-full overflow-hidden">
                        <div 
                          className={`h-full ${color} transition-all duration-500`}
                          style={{ width: `${percentage}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Recent Agents */}
              <div className="mt-6">
                <h4 className="text-sm font-medium text-muted-foreground mb-3">Recently Active</h4>
                <div className="space-y-2">
                  {agents
                    .filter(a => a.last_active)
                    .sort((a, b) => 
                      new Date(b.last_active || '').getTime() - new Date(a.last_active || '').getTime()
                    )
                    .slice(0, 5)
                    .map(agent => (
                      <button
                        key={agent.agent_id}
                        onClick={() => {
                          onSelectAgent(agent.agent_id);
                          onClose();
                        }}
                        className="w-full flex items-center gap-3 p-2 hover:bg-accent rounded-lg transition-colors text-left"
                      >
                        <div className={`
                          w-2 h-2 rounded-full
                          ${agent.status === 'online' ? 'bg-green-500' : ''}
                          ${agent.status === 'busy' ? 'bg-yellow-500' : ''}
                          ${agent.status === 'offline' ? 'bg-gray-500' : ''}
                          ${agent.status === 'error' ? 'bg-red-500' : ''}
                        `} />
                        <span className="flex-1 text-sm truncate">{agent.name}</span>
                        <span className="text-xs text-muted-foreground">
                          {agent.last_active && new Date(agent.last_active).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      </button>
                    ))}
                </div>
              </div>
            </div>

            {/* Recent Jobs */}
            <div className="space-y-4">
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <Cpu className="h-5 w-5" />
                Recent Jobs
              </h3>
              
              {recentJobs.length === 0 ? (
                <div className="p-8 text-center text-muted-foreground bg-muted/30 rounded-xl">
                  <Clock className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  <p>No recent jobs</p>
                </div>
              ) : (
                <div className="space-y-2 max-h-[400px] overflow-y-auto">
                  {recentJobs.map((job) => (
                    <div 
                      key={job.job_id}
                      className="p-3 bg-muted/50 rounded-lg border border-border"
                    >
                      <div className="flex items-center gap-2">
                        {job.status === 'completed' && <CheckCircle2 className="h-4 w-4 text-green-500" />}
                        {job.status === 'in_progress' && <Activity className="h-4 w-4 text-blue-500 animate-pulse" />}
                        {job.status === 'pending' && <Clock className="h-4 w-4 text-yellow-500" />}
                        {job.status === 'failed' && <AlertTriangle className="h-4 w-4 text-red-500" />}
                        
                        <span className="flex-1 text-sm font-medium truncate">{job.title}</span>
                        
                        <span className={`
                          text-[10px] px-1.5 py-0.5 rounded
                          ${job.status === 'completed' ? 'bg-green-500/20 text-green-400' : ''}
                          ${job.status === 'in_progress' ? 'bg-blue-500/20 text-blue-400' : ''}
                          ${job.status === 'pending' ? 'bg-yellow-500/20 text-yellow-400' : ''}
                          ${job.status === 'failed' ? 'bg-red-500/20 text-red-400' : ''}
                        `}>
                          {job.status}
                        </span>
                      </div>
                      
                      {job.description && (
                        <p className="text-xs text-muted-foreground mt-1 line-clamp-1">{job.description}</p>
                      )}
                      
                      <div className="flex items-center gap-2 mt-2 text-[10px] text-muted-foreground">
                        <span>Priority: {job.priority}</span>
                        <span>•</span>
                        <span>{new Date(job.created_at || '').toLocaleDateString()}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}