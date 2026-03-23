/**
 * SYSTVETAM — GTM Engine Floor
 * Zentraux Group LLC
 *
 * Jordan Reese + Taylor Moss. Floor index 4.
 * The sales floor. Revenue in motion.
 * Crew cards, pipeline task list, empty state.
 */

import { Phone, Megaphone, TrendingUp } from 'lucide-react';
import { useCrewRoster } from '@/api/crew';
import { useListTasks } from '@/api/tasks';
import { TaskCard } from '@/components/TaskCard';
import { statusColorMap, statusAnimationMap, type CrewStatusKey } from '@/design/tokens';
import type { CrewMember } from '@/types';

export function GTM() {
  const { data: crewData, isLoading: crewLoading } = useCrewRoster({ department: 'GTM' });
  const { data: tasksData, isLoading: tasksLoading } = useListTasks({ department: 'GTM' });

  const crew = crewData?.crew ?? [];
  const tasks = tasksData?.tasks ?? [];
  const activeCount = tasks.filter((t) =>
    !['RECEIPTED', 'FAILED'].includes(t.status)
  ).length;

  // Pipeline stats from task types
  const campaignCount = tasks.filter((t) => t.task_type === 'GTM_CAMPAIGN').length;
  const outreachCount = tasks.filter((t) => t.task_type === 'VOICE_OUTREACH').length;

  return (
    <div className="h-full flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-mono font-semibold tracking-[0.15em] text-gold">
            GTM ENGINE
          </h2>
          <p className="text-xxs font-mono text-glass-muted mt-0.5">
            JORDAN REESE — CLOSER
          </p>
        </div>
        <span className="text-xxs font-mono px-1.5 py-0.5 rounded bg-status-idle/20 text-status-idle">
          {activeCount} tasks
        </span>
      </div>

      {/* Pipeline Stats */}
      <div className="grid grid-cols-3 gap-2">
        <StatCard
          icon={<TrendingUp className="w-4 h-4" />}
          label="ACTIVE PIPELINE"
          count={activeCount}
          loading={tasksLoading}
        />
        <StatCard
          icon={<Megaphone className="w-4 h-4" />}
          label="CAMPAIGNS"
          count={campaignCount}
          loading={tasksLoading}
        />
        <StatCard
          icon={<Phone className="w-4 h-4" />}
          label="OUTREACH"
          count={outreachCount}
          loading={tasksLoading}
        />
      </div>

      {/* Crew Grid — 2 cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {crewLoading
          ? Array.from({ length: 2 }).map((_, i) => (
              <div key={i} className="glass-panel h-24 animate-pulse" />
            ))
          : crew.map((member) => (
              <GTMCrewCard key={member.callsign} member={member} />
            ))
        }
      </div>

      {/* Task List */}
      <div className="flex-1 min-h-0 flex flex-col">
        <span className="text-xxs font-mono text-glass-muted tracking-wider mb-2">
          GTM TASKS
        </span>

        <div className="flex-1 overflow-y-auto scrollbar-none space-y-1.5">
          {tasksLoading ? (
            Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="glass-panel h-12 animate-pulse" />
            ))
          ) : tasks.length === 0 ? (
            <div className="flex items-center justify-center gap-2 py-8 text-glass-muted">
              <Phone className="w-4 h-4 text-glass-muted/30" />
              <span className="text-xs font-mono tracking-wider">
                Pipeline clear — Jordan is prospecting
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

function StatCard({ icon, label, count, loading }: {
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
// GTM Crew Card
// ---------------------------------------------------------------------------

function GTMCrewCard({ member }: { member: CrewMember }) {
  const statusKey = member.status as CrewStatusKey;
  const color = statusColorMap[statusKey] ?? '#444455';
  const animation = statusAnimationMap[statusKey] ?? '';
  const isJordan = member.callsign === 'jordan-reese';

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
        {isJordan && (
          <span className="text-xxs font-mono text-gold/60 ml-auto">LEAD</span>
        )}
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
          <span className="text-xxs font-mono text-glass-muted/50">IDLE</span>
        )}
      </div>
    </div>
  );
}
