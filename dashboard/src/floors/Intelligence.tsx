/**
 * SYSTVETAM — Intelligence Floor
 * Zentraux Group LLC
 *
 * Clyde Nakamura's domain. Floor index 2.
 * Signal dashboard: inbound signals, active analysis, reports filed.
 * Single crew card (Clyde). Task list filtered to INTELLIGENCE.
 */

import { Radio, Activity, FileCheck, Search } from 'lucide-react';
import { useCrewRoster } from '@/api/crew';
import { useListTasks } from '@/api/tasks';
import { TaskCard } from '@/components/TaskCard';
import { statusColorMap, statusAnimationMap, type CrewStatusKey } from '@/design/tokens';
import type { CrewMember } from '@/types';

export function Intelligence() {
  const { data: crewData, isLoading: crewLoading } = useCrewRoster({ department: 'INTELLIGENCE' });
  const { data: tasksData, isLoading: tasksLoading } = useListTasks({ department: 'INTELLIGENCE' });

  const crew = crewData?.crew ?? [];
  const tasks = tasksData?.tasks ?? [];

  // Signal counts
  const inboundCount = tasks.filter((t) => t.status === 'NEW').length;
  const activeCount = tasks.filter((t) => t.status === 'EXECUTING').length;
  const filedCount = tasks.filter((t) =>
    t.status === 'RECEIPTED' || t.status === 'COMPLETE'
  ).length;
  const totalActive = tasks.filter((t) =>
    !['RECEIPTED', 'FAILED'].includes(t.status)
  ).length;

  return (
    <div className="h-full flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-mono font-semibold tracking-[0.15em] text-gold">
            INTELLIGENCE
          </h2>
          <p className="text-xxs font-mono text-glass-muted mt-0.5">
            CLYDE NAKAMURA — SIGNAL ENGINE
          </p>
        </div>
        <span className="text-xxs font-mono px-1.5 py-0.5 rounded bg-status-idle/20 text-status-idle">
          {totalActive} tasks
        </span>
      </div>

      {/* Signal Cards — 3-col grid */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
        <SignalCard
          icon={<Radio className="w-4 h-4" />}
          label="INBOUND SIGNALS"
          count={inboundCount}
          loading={tasksLoading}
        />
        <SignalCard
          icon={<Activity className="w-4 h-4" />}
          label="ACTIVE ANALYSIS"
          count={activeCount}
          loading={tasksLoading}
        />
        <SignalCard
          icon={<FileCheck className="w-4 h-4" />}
          label="REPORTS FILED"
          count={filedCount}
          loading={tasksLoading}
        />
      </div>

      {/* Clyde Crew Card — single, full-width */}
      <div>
        <span className="text-xxs font-mono text-glass-muted tracking-wider mb-2 block">
          OPERATOR
        </span>
        {crewLoading ? (
          <div className="glass-panel h-24 animate-pulse" />
        ) : crew.length > 0 ? (
          <ClydeCard member={crew[0]!} />
        ) : (
          <div className="glass-panel px-3 py-3 h-24 flex items-center justify-center">
            <span className="text-xs font-mono text-glass-muted">Clyde not found in roster</span>
          </div>
        )}
      </div>

      {/* Task List */}
      <div className="flex-1 min-h-0 flex flex-col">
        <span className="text-xxs font-mono text-glass-muted tracking-wider mb-2">
          INTELLIGENCE TASKS
        </span>

        <div className="flex-1 overflow-y-auto scrollbar-none space-y-1.5">
          {tasksLoading ? (
            Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="glass-panel h-12 animate-pulse" />
            ))
          ) : tasks.length === 0 ? (
            <div className="flex items-center justify-center gap-2 py-8 text-glass-muted">
              <Search className="w-4 h-4 text-glass-muted/30" />
              <span className="text-xs font-mono tracking-wider">
                No intelligence tasks — Clyde is scanning
              </span>
            </div>
          ) : (
            tasks.map((task) => (
              <TaskCard key={task.id} task={task} compact />
            ))
          )}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Signal Card — large number + label
// ---------------------------------------------------------------------------

interface SignalCardProps {
  icon: React.ReactNode;
  label: string;
  count: number;
  loading: boolean;
}

function SignalCard({ icon, label, count, loading }: SignalCardProps) {
  return (
    <div className="glass-panel px-4 py-4 flex flex-col items-center gap-2">
      <span className="text-gold/50">{icon}</span>
      {loading ? (
        <div className="w-8 h-8 rounded bg-glass-border animate-pulse" />
      ) : (
        <span className="text-2xl font-mono font-bold text-gold">{count}</span>
      )}
      <span className="text-xxs font-mono text-glass-muted tracking-wider text-center">
        {label}
      </span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Clyde Card — full-width crew card
// ---------------------------------------------------------------------------

function ClydeCard({ member }: { member: CrewMember }) {
  const statusKey = member.status as CrewStatusKey;
  const color = statusColorMap[statusKey] ?? '#444455';
  const animation = statusAnimationMap[statusKey] ?? '';

  return (
    <div className="glass-panel px-4 py-3 h-24 flex items-center gap-4">
      {/* Status dot — larger for single card */}
      <div
        className={`w-4 h-4 rounded-full shrink-0 ${animation}`}
        style={{ backgroundColor: color }}
      />

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-3">
          <span className="text-sm text-glass-text font-medium">
            {member.display_name}
          </span>
          <span className="text-xxs font-mono text-gold">{member.callsign}</span>
          {member.container_port && (
            <span className="text-xxs font-mono text-glass-muted/50">
              :{member.container_port}
            </span>
          )}
        </div>
        <p className="text-xxs font-mono text-glass-muted mt-0.5">{member.role}</p>
        <div className="mt-1">
          {member.current_task_ref ? (
            <span className="text-xxs font-mono text-gold-light">
              → {member.current_task_ref}
            </span>
          ) : (
            <span className="text-xxs font-mono text-glass-muted/50">IDLE — scanning</span>
          )}
        </div>
      </div>
    </div>
  );
}
