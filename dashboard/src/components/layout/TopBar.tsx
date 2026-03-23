/**
 * SYSTVETAM — Top Bar
 * Zentraux Group LLC
 *
 * Left:   SYSTVETAM wordmark + lotus (gold)
 * Center: current floor name
 * Right:  WS status dot + agent identity badge
 */

import { useTowerStore } from '@/store';
import { Hexagon, Wifi, WifiOff } from 'lucide-react';

interface TopBarProps {
  floorName: string;
}

export function TopBar({ floorName }: TopBarProps) {
  const wsConnected = useTowerStore((s) => s.wsConnected);
  const currentUser = useTowerStore((s) => s.currentUser);

  return (
    <header className="flex items-center justify-between px-4 py-3 bg-obsidian-surface/80 backdrop-blur-md border-b border-glass-border">
      {/* Left: Wordmark */}
      <div className="flex items-center gap-2.5 min-w-0">
        <Hexagon className="w-5 h-5 text-gold shrink-0" strokeWidth={1.5} />
        <span className="text-sm font-mono font-semibold tracking-[0.2em] text-gold truncate">
          SYSTVETAM
        </span>
      </div>

      {/* Center: Floor Name */}
      <div className="absolute left-1/2 -translate-x-1/2">
        <span className="text-xs font-mono tracking-widest uppercase text-glass-muted">
          {floorName}
        </span>
      </div>

      {/* Right: Status + Identity */}
      <div className="flex items-center gap-3 min-w-0">
        {/* WebSocket status */}
        <div className="flex items-center gap-1.5" title={wsConnected ? 'Live' : 'Disconnected'}>
          {wsConnected ? (
            <Wifi className="w-3.5 h-3.5 text-status-active" />
          ) : (
            <WifiOff className="w-3.5 h-3.5 text-status-error" />
          )}
          <span
            className={`w-1.5 h-1.5 rounded-full ${
              wsConnected ? 'bg-status-active' : 'bg-status-error animate-pulse-red'
            }`}
          />
        </div>

        {/* Agent identity */}
        {currentUser && (
          <div className="flex items-center gap-1.5 pl-2 border-l border-glass-border">
            <span className="text-xxs font-mono text-gold-light truncate max-w-[80px]">
              {currentUser.agent_id}
            </span>
            <span className="text-xxs font-mono text-glass-muted">
              {currentUser.role === 'SUPERUSER' ? '★' : currentUser.role === 'OPERATOR' ? '◆' : '○'}
            </span>
          </div>
        )}
      </div>
    </header>
  );
}
