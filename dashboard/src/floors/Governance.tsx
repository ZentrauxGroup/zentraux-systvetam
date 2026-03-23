/**
 * SYSTVETAM — Governance Floor
 * Zentraux Group LLC
 *
 * Victoria "Tori" Delgado + Maestra Voss. Floor index 8.
 * Order. Accountability. The infrastructure of trust.
 * Alert detection, compliance stats, governance task queue.
 */

import { Shield, AlertTriangle, FileCheck, Scale } from 'lucide-react';
import { useCrewRoster } from '@/api/crew';
import { useListTasks } from '@/api/tasks';
import { TaskCard } from '@/components/TaskCard';
import { statusColorMap, statusAnimationMap, type CrewStatusKey } from '@/design/tokens';
import type { CrewMember, Task } from '@/types';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const TERMINAL = new Set(['RECEIPTED', 'FAILED']);

function isActive(t: Task): boolean {
  return !TERMINAL.has(t.status);
}

export function Governance() {
  const { data: crewData, isLoading: crewLoading } = useCrewRoster({ department: 'GOVERNANCE' });
  const { data: tasksData, isLoading: tasksLoading } = useListTasks({ department: 'GOVERNANCE' });

  const crew = crewData?.crew ?? [];
  const tasks = tasksData?.tasks ?? [];

  const activeCount = tasks.filter(isActive).length;
  const hasCritical = tasks.some((t) => t.priority === 1 && isActive(t));

  // Stat counts
  const openCRs = tasks.filter((t) => t.task_type === 'CHANGE_REQUEST' && isActive(t)).length;
  const totalTasks = tasks.length;
  const receiptedTasks = tasks.filter((t) => t.status === 'RECEIPTED').length;
  const complianceRate = totalTasks > 0
    ? Math.round((receiptedTasks / totalTasks) * 100)
    : null;

  return (
    <div className="h-full flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div>
            <h2 className="text-sm font-mono font-semibold tracking-[0.15em] text-gold">
              GOVERNANCE
            </h2>
            <p className="text-xxs font-mono text-glass-muted mt-0.5">
              TORI DELGADO + MAESTRA VOSS
            </p>
          </div>
          {hasCritical && (
            <span className="
              flex items-center gap-1 text-xxs font-mono px-2 py-0.5 rounded
              bg-status-error/20 text-status-error animate-gate-ring
              border border-status-error/30
            ">
              <AlertTriangle className="w-3 h-3" />
              ALERT
            </span>
          )}
        </div>
        <span className="text-xxs font-mono px-1.5 py-0.5 rounded bg-status-idle/20 text-status-idle">
          {activeCount} tasks
        </span>
      </div>

      {/* Crew Grid — 2 cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {crewLoading
          ? Array.from({ length: 2 }).map((_, i) => (
              <div key={i} className="glass-panel h-24 animate-pulse" />
            ))
          : crew.map((member) => (
              <GovCrewCard key={member.callsign} member={member} />
            ))
        }
      </div>

      {/* Stat Row */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
        <GovStat
          icon={<FileCheck className="w-4 h-4" />}
          label="OPEN CHANGE REQUESTS"
          value={String(openCRs)}
          loading={tasksLoading}
        />
        <GovStat
          icon={<AlertTriangle className="w-4 h-4" />}
          label="OPEN BOARD ALERTS"
          value={String(tasks.filter((t) => t.priority === 1 && isActive(t)).length)}
          loading={tasksLoading}
        />
        <GovStat
          icon={<Scale className="w-4 h-4" />}
          label="COMPLIANCE RATE"
          value={complianceRate !== null ? `${complianceRate}%` : 'N/A'}
          loading={tasksLoading}
        />
      </div>

      {/* Task List */}
      <div className="flex-1 min-h-0 flex flex-col">
        <span className="text-xxs font-mono text-glass-muted tracking-wider mb-2">
          GOVERNANCE QUEUE
        </span>

        <div className="flex-1 overflow-y-auto scrollbar-none space-y-1.5">
          {tasksLoading ? (
            Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="glass-panel h-12 animate-pulse" />
            ))
          ) : tasks.length === 0 ? (
            <div className="flex items-center justify-center gap-2 py-8 text-glass-muted">
              <Shield className="w-4 h-4 text-gold/30" />
              <span className="text-xs font-mono tracking-wider">
                Governance queue clear — order maintained
              </span>
            </div>
          ) : (
            tasks.map((task) => (
              <div
                key={task.id}
                className={
                  task.priority === 1 && isActive(task)
                    ? 'border-l-2 border-red-500 rounded-circuit'
                    : ''
                }
              >
                <TaskCard task={task} compact />
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Governance Stat Card
// ---------------------------------------------------------------------------

function GovStat({ icon, label, value, loading }: {
  icon: React.ReactNode;
  label: string;
  value: string;
  loading: boolean;
}) {
  return (
    <div className="glass-panel px-4 py-4 flex flex-col items-center gap-1.5">
      <span className="text-gold/50">{icon}</span>
      {loading ? (
        <div className="w-8 h-8 rounded bg-glass-border animate-pulse" />
      ) : (
        <span className="text-2xl font-mono font-bold text-gold">{value}</span>
      )}
      <span className="text-xxs font-mono text-glass-muted tracking-wider text-center">
        {label}
      </span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Governance Crew Card
// ---------------------------------------------------------------------------

const IDLE_TEXT: Record<string, string> = {
  'tori-delgado': 'IDLE — standing watch',
  'maestra-voss': 'IDLE — compliance nominal',
};

function GovCrewCard({ member }: { member: CrewMember }) {
  const statusKey = member.status as CrewStatusKey;
  const color = statusColorMap[statusKey] ?? '#444455';
  const animation = statusAnimationMap[statusKey] ?? '';

  return (
    <div className="glass-panel px-3 py-3 h-24 flex flex-col justify-between">
      <div className="flex items-center gap-2">
        <div
          className={`w-2.5 h-2.5 rounded-full shrink-0 ${animation}`}
          style={{ backgroundColor: color }}
        />
        <span className="text-sm text-glass-text font-medium truncate">
          {member.display_name}
        </span>
      </div>

      <div className="ml-[18px]">
        <span className="text-xxs font-mono text-gold">{member.callsign}</span>
        <span className="text-xxs font-mono text-glass-muted ml-2 truncate">
          {member.role}
        </span>
      </div>

      <div className="ml-[18px]">
        {member.current_task_ref ? (
          <span className="text-xxs font-mono text-gold-light">
            → {member.current_task_ref}
          </span>
        ) : (
          <span className="text-xxs font-mono text-glass-muted/50">
            {IDLE_TEXT[member.callsign] ?? 'IDLE'}
          </span>
        )}
      </div>
    </div>
  );
}
