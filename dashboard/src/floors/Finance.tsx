/**
 * SYSTVETAM — Finance Floor
 * Zentraux Group LLC
 *
 * Maya Lin + Kimberly "Kim" Sato. Floor index 6.
 * The ledger. Every dollar accounted for.
 * MRR placeholder (Stripe sync pending), receipt stats, task list.
 */

import { Coins, Receipt, Activity } from 'lucide-react';
import { useCrewRoster } from '@/api/crew';
import { useListTasks } from '@/api/tasks';
import { TaskCard } from '@/components/TaskCard';
import { statusColorMap, statusAnimationMap, type CrewStatusKey } from '@/design/tokens';
import type { CrewMember } from '@/types';

export function Finance() {
  const { data: crewData, isLoading: crewLoading } = useCrewRoster({ department: 'FINANCE' });
  const { data: tasksData, isLoading: tasksLoading } = useListTasks({ department: 'FINANCE' });

  const crew = crewData?.crew ?? [];
  const tasks = tasksData?.tasks ?? [];

  const receiptedCount = tasks.filter((t) => t.status === 'RECEIPTED').length;
  const activeCount = tasks.filter((t) =>
    !['RECEIPTED', 'FAILED'].includes(t.status)
  ).length;

  return (
    <div className="h-full flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-mono font-semibold tracking-[0.15em] text-gold">
            FINANCE
          </h2>
          <p className="text-xxs font-mono text-glass-muted mt-0.5">
            MAYA LIN + KIM SATO
          </p>
        </div>
        <span className="text-xxs font-mono px-1.5 py-0.5 rounded bg-status-idle/20 text-status-idle">
          {activeCount} tasks
        </span>
      </div>

      {/* Stat Row */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
        {/* MRR — static placeholder */}
        <div className="glass-panel px-4 py-4 flex flex-col items-center gap-1.5">
          <Coins className="w-4 h-4 text-gold/50" />
          <span className="text-2xl font-mono font-bold text-gold">$0.00</span>
          <span className="text-xxs font-mono text-glass-muted tracking-wider text-center">
            MONTHLY RECURRING REVENUE
          </span>
          <span className="text-[9px] font-mono text-glass-muted/40 tracking-wider">
            STRIPE SYNC PENDING
          </span>
        </div>

        {/* Receipted Transactions */}
        <div className="glass-panel px-4 py-4 flex flex-col items-center gap-1.5">
          <Receipt className="w-4 h-4 text-gold/50" />
          {tasksLoading ? (
            <div className="w-8 h-8 rounded bg-glass-border animate-pulse" />
          ) : (
            <span className="text-2xl font-mono font-bold text-gold">{receiptedCount}</span>
          )}
          <span className="text-xxs font-mono text-glass-muted tracking-wider text-center">
            RECEIPTED TRANSACTIONS
          </span>
        </div>

        {/* Active Tasks */}
        <div className="glass-panel px-4 py-4 flex flex-col items-center gap-1.5">
          <Activity className="w-4 h-4 text-gold/50" />
          {tasksLoading ? (
            <div className="w-8 h-8 rounded bg-glass-border animate-pulse" />
          ) : (
            <span className="text-2xl font-mono font-bold text-gold">{activeCount}</span>
          )}
          <span className="text-xxs font-mono text-glass-muted tracking-wider text-center">
            ACTIVE TASKS
          </span>
        </div>
      </div>

      {/* Crew Grid — 2 cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {crewLoading
          ? Array.from({ length: 2 }).map((_, i) => (
              <div key={i} className="glass-panel h-24 animate-pulse" />
            ))
          : crew.map((member) => (
              <FinanceCrewCard key={member.callsign} member={member} />
            ))
        }
      </div>

      {/* Task List */}
      <div className="flex-1 min-h-0 flex flex-col">
        <span className="text-xxs font-mono text-glass-muted tracking-wider mb-2">
          ACTIVE FINANCE TASKS
        </span>

        <div className="flex-1 overflow-y-auto scrollbar-none space-y-1.5">
          {tasksLoading ? (
            Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="glass-panel h-12 animate-pulse" />
            ))
          ) : tasks.length === 0 ? (
            <div className="flex items-center justify-center gap-2 py-8 text-glass-muted">
              <Coins className="w-4 h-4 text-gold/30" />
              <span className="text-xs font-mono tracking-wider">
                Ledger clear — runway stable
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
// Finance Crew Card
// ---------------------------------------------------------------------------

const IDLE_TEXT: Record<string, string> = {
  'maya-lin': 'IDLE — monitoring runway',
  'kim-sato': 'IDLE — audit ready',
};

function FinanceCrewCard({ member }: { member: CrewMember }) {
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
