/**
 * SYSTVETAM — Task Card
 * Zentraux Group LLC
 *
 * Reusable display card for any task in any floor.
 * No mutations — display only. Click to expand inline.
 */

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, Circle } from 'lucide-react';
import type { Task, TaskStatus } from '@/types';

// ---------------------------------------------------------------------------
// Status → badge color mapping
// ---------------------------------------------------------------------------

const STATUS_COLORS: Record<TaskStatus, { bg: string; text: string }> = {
  NEW:       { bg: 'bg-status-idle/20',      text: 'text-status-idle' },
  ASSIGNED:  { bg: 'bg-status-idle/20',      text: 'text-status-idle' },
  EXECUTING: { bg: 'bg-gold-muted',          text: 'text-gold' },
  QA_GATE:   { bg: 'bg-status-gate/20',      text: 'text-status-gate' },
  LEVI_GATE: { bg: 'bg-status-gate/20',      text: 'text-status-gate' },
  DEPLOYING: { bg: 'bg-gold-muted',          text: 'text-gold-light' },
  COMPLETE:  { bg: 'bg-status-active/15',    text: 'text-status-active' },
  RECEIPTED: { bg: 'bg-status-active/10',    text: 'text-status-active/70' },
  FAILED:    { bg: 'bg-status-error/20',     text: 'text-status-error' },
};

const PRIORITY_COLORS: Record<number, string> = {
  1: 'text-status-error',    // CRITICAL
  2: 'text-status-gate',     // HIGH
  3: 'text-glass-muted',     // NORMAL
  4: 'text-glass-muted/50',  // LOW
  5: 'text-glass-muted/30',  // BACKLOG
};

const PRIORITY_LABELS: Record<number, string> = {
  1: 'CRITICAL', 2: 'HIGH', 3: 'NORMAL', 4: 'LOW', 5: 'BACKLOG',
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatTimestamp(ts: string | null): string {
  if (!ts) return '—';
  const d = new Date(ts);
  return d.toLocaleString('en-US', {
    month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit',
    hour12: false, timeZone: 'America/Phoenix',
  });
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface TaskCardProps {
  task: Task;
  compact?: boolean;
}

export function TaskCard({ task, compact = false }: TaskCardProps) {
  const [expanded, setExpanded] = useState(false);
  const statusStyle = STATUS_COLORS[task.status] ?? STATUS_COLORS.NEW;
  const priorityColor = PRIORITY_COLORS[task.priority] ?? PRIORITY_COLORS[3];

  return (
    <div
      onClick={() => setExpanded((p) => !p)}
      className="glass-panel-interactive cursor-pointer px-3 py-2.5"
    >
      {/* Main row */}
      <div className="flex items-center gap-2.5 min-w-0">
        {/* Priority dot */}
        <Circle className={`w-2 h-2 shrink-0 fill-current ${priorityColor}`} />

        {/* Task ref */}
        <span className="text-xs font-mono font-semibold text-gold shrink-0">
          {task.task_ref}
        </span>

        {/* Title */}
        <span className="text-sm text-glass-text truncate flex-1">
          {task.title}
        </span>

        {/* Status badge */}
        <span className={`
          text-xxs font-mono px-1.5 py-0.5 rounded
          ${statusStyle.bg} ${statusStyle.text} shrink-0
        `}>
          {task.status}
        </span>

        {/* Expand chevron */}
        {!compact && (
          <ChevronDown className={`
            w-3.5 h-3.5 text-glass-muted shrink-0 transition-transform duration-200
            ${expanded ? 'rotate-180' : ''}
          `} />
        )}
      </div>

      {/* Subtitle row (compact shows this inline) */}
      {!compact && (
        <div className="flex items-center gap-3 mt-1.5 ml-[18px]">
          {task.department && (
            <span className="text-xxs font-mono text-glass-muted">{task.department}</span>
          )}
          <span className="text-xxs font-mono text-glass-muted/50">
            {PRIORITY_LABELS[task.priority] ?? 'P' + task.priority}
          </span>
          {task.assigned_to && (
            <span className="text-xxs font-mono text-gold-dark">
              → {task.assigned_to.slice(0, 8)}
            </span>
          )}
        </div>
      )}

      {/* Expanded detail panel */}
      <AnimatePresence>
        {expanded && !compact && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="mt-3 pt-3 border-t border-glass-border ml-[18px] space-y-2">
              {/* Description */}
              {task.description && (
                <p className="text-xs text-glass-text/80 leading-relaxed">
                  {task.description}
                </p>
              )}

              {/* Timestamps grid */}
              <div className="grid grid-cols-2 gap-x-4 gap-y-1">
                <TsRow label="Created" ts={task.created_at} />
                <TsRow label="Assigned" ts={task.assigned_at} />
                <TsRow label="Executing" ts={task.executing_at} />
                <TsRow label="Completed" ts={task.completed_at} />
                <TsRow label="Receipted" ts={task.receipted_at} />
              </div>

              {/* Levi note */}
              {task.levi_note && (
                <div className="text-xs">
                  <span className="text-gold-dark font-mono">LEVI NOTE: </span>
                  <span className="text-glass-text/70">{task.levi_note}</span>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function TsRow({ label, ts }: { label: string; ts: string | null }) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-xxs font-mono text-glass-muted w-16">{label}</span>
      <span className="text-xxs font-mono text-glass-text/60">{formatTimestamp(ts)}</span>
    </div>
  );
}
