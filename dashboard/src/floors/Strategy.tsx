/**
 * SYSTVETAM — Strategy Floor
 * Zentraux Group LLC
 *
 * Dr. Isabella "NOVA" Reyes. Floor index 5.
 * Intelligence. The map of the competitive landscape.
 * Solo crew card, briefing stats, strategy task list.
 */

import { Compass, BookOpen, Target, Eye } from 'lucide-react';
import { useCrewRoster } from '@/api/crew';
import { useListTasks } from '@/api/tasks';
import { TaskCard } from '@/components/TaskCard';
import { statusColorMap, statusAnimationMap, type CrewStatusKey } from '@/design/tokens';
import type { CrewMember } from '@/types';

export function Strategy() {
  const { data: crewData, isLoading: crewLoading } = useCrewRoster({ department: 'STRATEGY' });
  const { data: tasksData, isLoading: tasksLoading } = useListTasks({ department: 'STRATEGY' });

  const crew = crewData?.crew ?? [];
  const tasks = tasksData?.tasks ?? [];

  const activeCount = tasks.filter((t) =>
    !['RECEIPTED', 'FAILED'].includes(t.status)
  ).length;
  const filedCount = tasks.filter((t) =>
    t.status === 'RECEIPTED' || t.status === 'COMPLETE'
  ).length;

  return (
    <div className="h-full flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-mono font-semibold tracking-[0.15em] text-gold">
            STRATEGY
          </h2>
          <p className="text-xxs font-mono text-glass-muted mt-0.5">
            DR. ISABELLA REYES — NOVA
          </p>
        </div>
        <span className="text-xxs font-mono px-1.5 py-0.5 rounded bg-status-idle/20 text-status-idle">
          {activeCount} active
        </span>
      </div>

      {/* Strategy Stats */}
      <div className="grid grid-cols-3 gap-2">
        <StratCard
          icon={<Target className="w-4 h-4" />}
          label="ACTIVE"
          count={activeCount}
          loading={tasksLoading}
        />
        <StratCard
          icon={<BookOpen className="w-4 h-4" />}
          label="BRIEFINGS FILED"
          count={filedCount}
          loading={tasksLoading}
        />
        <StratCard
          icon={<Eye className="w-4 h-4" />}
          label="IN REVIEW"
          count={tasks.filter((t) => t.status === 'QA_GATE' || t.status === 'LEVI_GATE').length}
          loading={tasksLoading}
        />
      </div>

      {/* Nova Crew Card — single, full-width */}
      <div>
        <span className="text-xxs font-mono text-glass-muted tracking-wider mb-2 block">
          OPERATOR
        </span>
        {crewLoading ? (
          <div className="glass-panel h-24 animate-pulse" />
        ) : crew.length > 0 ? (
          <NovaCard member={crew[0]!} />
        ) : (
          <div className="glass-panel px-3 py-3 h-24 flex items-center justify-center">
            <span className="text-xs font-mono text-glass-muted">NOVA not found in roster</span>
          </div>
        )}
      </div>

      {/* Task List */}
      <div className="flex-1 min-h-0 flex flex-col">
        <span className="text-xxs font-mono text-glass-muted tracking-wider mb-2">
          STRATEGY TASKS
        </span>

        <div className="flex-1 overflow-y-auto scrollbar-none space-y-1.5">
          {tasksLoading ? (
            Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="glass-panel h-12 animate-pulse" />
            ))
          ) : tasks.length === 0 ? (
            <div className="flex items-center justify-center gap-2 py-8 text-glass-muted">
              <Compass className="w-4 h-4 text-glass-muted/30" />
              <span className="text-xs font-mono tracking-wider">
                Strategy queue clear — NOVA is observing
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
// Stat Card
// ---------------------------------------------------------------------------

function StratCard({ icon, label, count, loading }: {
  icon: React.ReactNode;
  label: string;
  count: number;
  loading: boolean;
}) {
  return (
    <div className="glass-panel px-3 py-3 flex flex-col items-center gap-1.5">
      <span className="text-gold/50">{icon}</span>
      {loading ? (
        <div className="w-6 h-6 rounded bg-glass-border animate-pulse" />
      ) : (
        <span className="text-xl font-mono font-bold text-gold">{count}</span>
      )}
      <span className="text-xxs font-mono text-glass-muted tracking-wider text-center">
        {label}
      </span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Nova Card — full-width solo crew card
// ---------------------------------------------------------------------------

function NovaCard({ member }: { member: CrewMember }) {
  const statusKey = member.status as CrewStatusKey;
  const color = statusColorMap[statusKey] ?? '#444455';
  const animation = statusAnimationMap[statusKey] ?? '';

  return (
    <div className="glass-panel px-4 py-3 h-24 flex items-center gap-4">
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
        </div>
        <p className="text-xxs font-mono text-glass-muted mt-0.5">{member.role}</p>
        <div className="mt-1">
          {member.current_task_ref ? (
            <span className="text-xxs font-mono text-gold-light">
              → {member.current_task_ref}
            </span>
          ) : (
            <span className="text-xxs font-mono text-glass-muted/50">IDLE — observing landscape</span>
          )}
        </div>
      </div>
    </div>
  );
}
