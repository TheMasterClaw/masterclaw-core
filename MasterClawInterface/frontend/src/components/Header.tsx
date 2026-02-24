import { User, Bell, Settings, Zap, Wifi, WifiOff, Activity, Server } from 'lucide-react';
import { ServerStats } from '../types';

interface HeaderProps {
  userName: string;
  isConnected: boolean;
  connectionError?: string | null;
  agentCount: number;
  onlineCount: number;
  stats?: ServerStats;
  onRefresh?: () => void;
}

export function Header({ 
  userName, 
  isConnected, 
  connectionError,
  agentCount,
  onlineCount,
  stats,
  onRefresh
}: HeaderProps) {
  return (
    <header className="h-14 bg-card border-b border-border flex items-center justify-between px-4">
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
            <Zap className="h-5 w-5 text-primary-foreground" />
          </div>
          <div>
            <h1 className="font-bold text-lg">MasterClaw</h1>
            <p className="text-[10px] text-muted-foreground">Agent Command Interface</p>
          </div>
        </div>

        <div className="h-6 w-px bg-border mx-2" />

        {/* Connection Status */}
        <div className="flex items-center gap-2">
          {isConnected ? (
            <>
              <Wifi className="h-4 w-4 text-green-500" />
              <span className="text-xs text-green-500">Connected</span>
            </>
          ) : (
            <>
              <WifiOff className="h-4 w-4 text-red-500" />
              <span className="text-xs text-red-500">
                {connectionError ? 'Error' : 'Disconnected'}
              </span>
            </>
          )}
        </div>

        <div className="h-6 w-px bg-border mx-2" />

        {/* Agent Stats */}
        <div className="hidden md:flex items-center gap-3 text-xs">
          <div className="flex items-center gap-1">
            <Server className="h-3 w-3 text-muted-foreground" />
            <span className="text-muted-foreground">Agents:</span>
            <span className="font-medium">{agentCount}</span>
          </div>
          <div className="flex items-center gap-1">
            <Activity className="h-3 w-3 text-muted-foreground" />
            <span className="text-muted-foreground">Online:</span>
            <span className="font-medium text-green-500">{onlineCount}</span>
          </div>
          {stats && (
            <>
              <div className="flex items-center gap-1">
                <span className="text-muted-foreground">Jobs:</span>
                <span className="font-medium text-yellow-500">{stats.jobs.pending + stats.jobs.inProgress}</span>
              </div>
            </>
          )}
        </div>
      </div>

      <div className="flex items-center gap-2">
        <button 
          onClick={onRefresh}
          className="p-2 hover:bg-accent rounded-lg transition-colors relative"
        >
          <Bell className="h-4 w-4" />
          {stats && stats.jobs.pending > 0 && (
            <span className="absolute top-1 right-1 h-2 w-2 bg-primary rounded-full animate-pulse" />
          )}
        </button>
        
        <button className="p-2 hover:bg-accent rounded-lg transition-colors">
          <Settings className="h-4 w-4" />
        </button>

        <div className="h-6 w-px bg-border mx-1" />

        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-accent rounded-full flex items-center justify-center">
            <User className="h-4 w-4" />
          </div>
          <div className="hidden sm:block">
            <p className="text-sm font-medium">{userName}</p>
            <p className="text-[10px] text-muted-foreground">Rex</p>
          </div>
        </div>
      </div>
    </header>
  );
}