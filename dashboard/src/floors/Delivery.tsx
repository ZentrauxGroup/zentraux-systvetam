/**
 * SYSTVETAM — Delivery Floor
 * Zentraux Group LLC
 *
 * Alex Harris. Floor index 7.
 * Momentum. Clients becoming partners. The work landing.
 * Milestone tracker, crew card, delivery task list.
 */

import { CheckCircle2, Circle, Package, Truck } from 'lucide-react';
import { useCrewRoster } from '@/api/crew';
import { useListTasks } from '@/api/tasks';
import { TaskCard } from '@/components/TaskCard';
import { statusColorMap, statusAnimationMap, type CrewStatusKey } from '@/design/tokens';
import type { CrewMember, Task } from '@/types';

// ---------------------------------------------------------------------------
// Milestone pipeline stage definitions
// ---------------------------------------------------------------------------

interface Stage {
  label: string;
  key: string;
  test: (t: Task) => boolean;
}

const STAGES: Stage[] = [
  { label: 'SIGNED',     key: 'signed',     test: (t) => t.status === 'NEW' },
  { label: 'CONFIGURED', key: 'configured', test: (t) => t.status === 'ASSIGNED' || t.status === 'EXECUTING' },
  { label: 'TRAINED',    key: 'trained',    test: (t) => t.status === 'QA_GATE' || t.status === 'LEVI_GATE' },
  { label: 'LIVE',       key: 'live',       test: (t) => t.status === 'DEPLOYING' || t.status === 'COMPLETE' },
  { label: 'RECEIPTED',  key: 'receipted',  test: (t) => t.status === 'RECEIPTED' },
];

export function Delivery() {
  const { data: crewData, isLoading: crewLoading } = useCrewRoster({ department: 'DELIVERY' });
  const { data: tasksData, isLoading: tasksLoading } = useListTasks({ department: 'DELIVERY' });

  const crew = crewData?.crew ?? [];
  const tasks = tasksData?.tasks ?? [];

  const activeCount = tasks.filter((t) =>
    !['RECEIPTED', 'FAILED'].includes(t.status)
  ).length;

  // Compute stage counts
  const stageCounts = STAGES.map((stage) => ({
    ...stage,
    count: tasks.filter(stage.test).length,
  }));

  const hasTasks = tasks.length > 0;

  return (
    <div className="h-full flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-mono font-semibold tracking-[0.15em] text-gold">
            DELIVERY
          </h2>
          <p className="text-xxs font-mono text-glass-muted mt-0.5">
            ALEX HARRIS — IMPLEMENTATION
          </p>
        </div>
        <span className="text-xxs font-mono px-1.5 py-0.5 rounded bg-status-idle/20 text-status-idle">
          {activeCount} tasks
        </span>
      </div>

      {/* Milestone Tracker */}
      <div className="glass-panel px-4 py-4">
        {!hasTasks && !tasksLoading ? (
          <div className="flex items-center justify-center gap-2 py-3 text-glass-muted">
            <Package className="w-4 h-4 text-glass-muted/30" />
            <span className="text-xs font-mono tracking-wider">No active pilots</span>
          </div>
        ) : (
          <div className="flex items-center justify-between gap-1">
            {stageCounts.map((stage, i) => {
              const isActive = stage.count > 0;
              const isPast = stageCounts.slice(i + 1).some((s) => s.count > 0);

              return (
                <div key={stage.key} className="flex items-center flex-1 min-w-0">
                  {/* Stage node */}
                  <div className="flex flex-col items-center gap-1.5 flex-1">
                    {/* Icon */}
                    {tasksLoading ? (
                      <div className="w-5 h-5 rounded-full bg-glass-border animate-pulse" />
                    ) : isPast || (isActive && stage.key === 'receipted') ? (
                      <CheckCircle2 className="w-5 h-5 text-status-active shrink-0" />
                    ) : isActive ? (
                      <div className="w-5 h-5 rounded-full border-2 border-gold bg-gold-muted animate-pulse-gold shrink-0" />
                    ) : (
                      <Circle className="w-5 h-5 text-glass-muted/30 shrink-0" />
                    )}

                    {/* Label */}
                    <span className={`
                      text-[9px] font-mono tracking-wider text-center leading-tight
                      ${isActive ? 'text-gold' : 'text-glass-muted/40'}
                    `}>
                      {stage.label}
                    </span>

                    {/* Count */}
                    {!tasksLoading && (
                      <span className={`
                        text-xs font-mono font-bold
                        ${isActive ? 'text-gold' : 'text-glass-muted/20'}
                      `}>
                        {stage.count}
                      </span>
                    )}
                  </div>

                  {/* Connector line (not after last) */}
                  {i < STAGES.length - 1 && (
                    <div className={`
                      h-px flex-1 mx-1
                      ${isPast || isActive ? 'bg-gold/30' : 'bg-glass-border'}
                    `} />
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Crew Card — single, max-w-lg */}
      <div>
        <span className="text-xxs font-mono text-glass-muted tracking-wider mb-2 block">
          OPERATOR
        </span>
        {crewLoading ? (
          <div className="glass-panel h-24 animate-pulse max-w-lg" />
        ) : crew.length > 0 ? (
          <AlexCard member={crew[0]!} />
        ) : (
          <div className="glass-panel px-3 py-3 h-24 flex items-center justify-center max-w-lg">
            <span className="text-xs font-mono text-glass-muted">Alex not found in roster</span>
          </div>
        )}
      </div>

      {/* Task List */}
      <div className="flex-1 min-h-0 flex flex-col">
        <span className="text-xxs font-mono text-glass-muted tracking-wider mb-2">
          ACTIVE DELIVERY TASKS
        </span>

        <div className="flex-1 overflow-y-auto scrollbar-none space-y-1.5">
          {tasksLoading ? (
            Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="glass-panel h-12 animate-pulse" />
            ))
          ) : tasks.length === 0 ? (
            <div className="flex items-center justify-center gap-2 py-8 text-glass-muted">
              <span className="w-2 h-2 rounded-full bg-status-active" />
              <span className="text-xs font-mono tracking-wider">
                Delivery queue clear — all pilots stable
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
// Alex Card — full-width solo crew card
// ---------------------------------------------------------------------------

function AlexCard({ member }: { member: CrewMember }) {
  const statusKey = member.status as CrewStatusKey;
  const color = statusColorMap[statusKey] ?? '#444455';
  const animation = statusAnimationMap[statusKey] ?? '';

  return (
    <div className="glass-panel px-4 py-3 h-24 flex items-center gap-4 max-w-lg">
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
            <span className="text-xxs font-mono text-glass-muted/50">
              IDLE — ready to onboard
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
