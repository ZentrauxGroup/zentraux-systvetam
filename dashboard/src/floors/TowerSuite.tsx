/**
 * SYSTVETAM — Tower Suite Floor
 * Zentraux Group LLC
 *
 * The Architect's command surface. Index 1.
 * 3-column grid: Tasks | Gate Queue | Crew + Receipts.
 * Filter tabs, task creation, full gate review interface.
 */

import { useState } from 'react';
import { Plus, Shield, AlertTriangle } from 'lucide-react';
import { useListTasks } from '@/api/tasks';
import { useGateQueue } from '@/api/gates';
import { useTowerStore } from '@/store';
import { TaskCard } from '@/components/TaskCard';
import { TaskCreateModal } from '@/components/TaskCreateModal';
import { GateQueueWidget } from '@/components/GateQueueWidget';
import { CrewPulseBar } from '@/components/CrewPulseBar';
import { ReceiptFeed } from '@/components/ReceiptFeed';
import type { Task } from '@/types';

// ---------------------------------------------------------------------------
// Filter tabs
// ---------------------------------------------------------------------------

type FilterTab = 'all' | 'mine' | 'critical';

const TABS: { key: FilterTab; label: string }[] = [
  { key: 'all', label: 'ALL' },
  { key: 'mine', label: 'MY TASKS' },
  { key: 'critical', label: 'CRITICAL' },
];

const ACTIVE_STATUSES = ['NEW', 'ASSIGNED', 'EXECUTING', 'QA_GATE', 'LEVI_GATE', 'DEPLOYING', 'COMPLETE'];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function TowerSuite() {
  const [activeTab, setActiveTab] = useState<FilterTab>('all');
  const [modalOpen, setModalOpen] = useState(false);
  const currentUser = useTowerStore((s) => s.currentUser);

  // Fetch all active tasks (not RECEIPTED, not FAILED)
  const { data: tasksData } = useListTasks({ limit: 200 });
  const { data: gateData } = useGateQueue();

  const allTasks = tasksData?.tasks ?? [];
  const activeTasks = allTasks.filter((t) => ACTIVE_STATUSES.includes(t.status));
  const gateCount = gateData?.total ?? 0;

  // Apply tab filter
  const filteredTasks = filterTasks(activeTasks, activeTab, currentUser?.agent_id ?? '');

  // Empty state messages per tab
  const emptyMessages: Record<FilterTab, string> = {
    all: 'No active tasks',
    mine: 'None assigned to you',
    critical: 'No critical tasks — system stable',
  };

  return (
    <div className="h-full flex flex-col gap-3">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-3">
          <h2 className="text-sm font-mono font-semibold tracking-[0.15em] text-gold">
            TOWER SUITE
          </h2>
          <span className="text-xxs font-mono px-1.5 py-0.5 rounded bg-status-idle/20 text-status-idle">
            {activeTasks.length} active
          </span>
          {gateCount > 0 && (
            <span className="text-xxs font-mono px-1.5 py-0.5 rounded bg-gold-muted text-gold animate-gate-ring">
              {gateCount} in gate
            </span>
          )}
        </div>

        <button
          onClick={() => setModalOpen(true)}
          className="
            flex items-center gap-1.5 px-3 py-1.5 rounded-circuit
            bg-gold/10 border border-gold/30 text-gold
            hover:bg-gold/20 hover:border-gold/50
            transition-all duration-200
            text-xxs font-mono tracking-wider
          "
        >
          <Plus className="w-3 h-3" />
          NEW TASK
        </button>
      </div>

      {/* 3-column grid */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-[40%_35%_25%] gap-3 min-h-0">
        {/* LEFT — Task List */}
        <div className="flex flex-col min-h-0">
          {/* Filter tabs */}
          <div className="flex gap-1 mb-2">
            {TABS.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`
                  px-2.5 py-1 rounded-circuit text-xxs font-mono tracking-wider
                  transition-all duration-150
                  ${activeTab === tab.key
                    ? 'bg-gold/15 text-gold border border-gold/25'
                    : 'text-glass-muted hover:text-glass-text border border-transparent'
                  }
                `}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Task list */}
          <div className="flex-1 overflow-y-auto scrollbar-none space-y-1.5">
            {filteredTasks.length === 0 ? (
              <div className="flex items-center justify-center gap-2 py-12 text-glass-muted">
                {activeTab === 'critical' ? (
                  <Shield className="w-4 h-4 text-status-active/50" />
                ) : (
                  <AlertTriangle className="w-4 h-4 text-glass-muted/30" />
                )}
                <span className="text-xs font-mono">{emptyMessages[activeTab]}</span>
              </div>
            ) : (
              filteredTasks.map((task) => (
                <TaskCard key={task.id} task={task} />
              ))
            )}
          </div>
        </div>

        {/* CENTER — Gate Queue */}
        <div className="flex flex-col min-h-0">
          <span className="text-xxs font-mono text-glass-muted tracking-wider mb-2">
            GATE QUEUE
          </span>
          <div className="flex-1 overflow-y-auto scrollbar-none">
            <GateQueueWidget />
          </div>
        </div>

        {/* RIGHT — Crew + Receipts */}
        <div className="flex flex-col min-h-0">
          <CrewPulseBar />
          <div className="border-t border-gold/10 my-2" />
          <span className="text-xxs font-mono text-glass-muted tracking-wider mb-2">
            RECEIPT FEED
          </span>
          <div className="flex-1 overflow-y-auto scrollbar-none">
            <ReceiptFeed />
          </div>
        </div>
      </div>

      {/* Task Create Modal */}
      <TaskCreateModal open={modalOpen} onClose={() => setModalOpen(false)} />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Filter logic
// ---------------------------------------------------------------------------

function filterTasks(tasks: Task[], tab: FilterTab, agentId: string): Task[] {
  switch (tab) {
    case 'mine':
      // MY TASKS: can't filter by UUID from agent_id alone — filter by requested_by
      return tasks.filter((t) => t.requested_by === agentId || t.assigned_to !== null);
    case 'critical':
      return tasks.filter((t) => t.priority === 1);
    default:
      return tasks;
  }
}
