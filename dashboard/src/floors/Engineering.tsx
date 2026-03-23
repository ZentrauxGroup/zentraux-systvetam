/**
 * SYSTVETAM — Engineering Floor
 * Zentraux Group LLC
 *
 * Department floor for ENGINEERING.
 * Marcus, Sophia, Jax, Riley, Noah, Rye, Len — 7 strong.
 * Top: crew cards with live status. Bottom: filtered task list.
 */

import { useCrewRoster } from '@/api/crew';
import { useListTasks } from '@/api/tasks';
import { TaskCard } from '@/components/TaskCard';
import { statusColorMap, statusAnimationMap, type CrewStatusKey } from '@/design/tokens';
import type { CrewMember } from '@/types';

export function Engineering() {
  const { data: crewData, isLoading: crewLoading } = useCrewRoster({ department: 'ENGINEERING' });
  const { data: tasksData, isLoading: tasksLoading } = useListTasks({ department: 'ENGINEERING' });

  const crew = crewData?.crew ?? [];
  const tasks = tasksData?.tasks ?? [];
  const activeCount = tasks.filter((t) =>
    !['RECEIPTED', 'FAILED'].includes(t.status)
  ).length;

  return (
    <div className="h-full flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-mono font-semibold tracking-[0.15em] text-gold">
            ENGINEERING
          </h2>
          <p className="text-xxs font-mono text-glass-muted mt-0.5">
            MARCUS REED — LEAD
          </p>
        </div>
        <span className="text-xxs font-mono px-1.5 py-0.5 rounded bg-status-idle/20 text-status-idle">
          {activeCount} tasks
        </span>
      </div>

      {/* Crew Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
        {crewLoading
          ? Array.from({ length: 7 }).map((_, i) => (
              <div key={i} className="glass-panel h-24 animate-pulse" />
            ))
          : crew.map((member) => (
              <CrewCard key={member.callsign} member={member} />
            ))
        }
      </div>

      {/* Task List */}
      <div className="flex-1 min-h-0 flex flex-col">
        <span className="text-xxs font-mono text-glass-muted tracking-wider mb-2">
          ACTIVE ENGINEERING TASKS
        </span>

        <div className="flex-1 overflow-y-auto scrollbar-none space-y-1.5">
          {tasksLoading ? (
            Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="glass-panel h-12 animate-pulse" />
            ))
          ) : tasks.length === 0 ? (
            <div className="flex items-center justify-center gap-2 py-8 text-glass-muted">
              <span className="w-2 h-2 rounded-full bg-status-active" />
              <span className="text-xs font-mono tracking-wider">Engineering queue clear</span>
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
// Crew Card — engineering-specific card with live status
// ---------------------------------------------------------------------------

function CrewCard({ member }: { member: CrewMember }) {
  const statusKey = member.status as CrewStatusKey;
  const color = statusColorMap[statusKey] ?? '#444455';
  const animation = statusAnimationMap[statusKey] ?? '';

  return (
    <div className="glass-panel px-3 py-3 h-24 flex flex-col justify-between">
      {/* Top row: dot + name */}
      <div className="flex items-center gap-2">
        <div
          className={`w-2.5 h-2.5 rounded-full shrink-0 ${animation}`}
          style={{ backgroundColor: color }}
        />
        <span className="text-sm text-glass-text font-medium truncate">
          {member.display_name}
        </span>
      </div>

      {/* Middle: callsign + role */}
      <div className="ml-[18px]">
        <span className="text-xxs font-mono text-gold">{member.callsign}</span>
        <span className="text-xxs font-mono text-glass-muted ml-2 truncate">
          {member.role}
        </span>
      </div>

      {/* Bottom: current task */}
      <div className="ml-[18px]">
        {member.current_task_ref ? (
          <span className="text-xxs font-mono text-gold-light">
            → {member.current_task_ref}
          </span>
        ) : (
          <span className="text-xxs font-mono text-glass-muted/50">IDLE</span>
        )}
      </div>
    </div>
  );
}
