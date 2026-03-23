/**
 * SYSTVETAM — Gate Queue Widget
 * Zentraux Group LLC
 *
 * The gold-ring queue. Tasks awaiting QA or Levi gate decisions.
 * CRITICAL items pulse with gate-ring animation.
 * FAIL/RETURN require inline note before submitting.
 */

import { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircle2, RotateCcw, XCircle, ShieldCheck, Send } from 'lucide-react';
import { useGateQueue, useGateApprove, useGateReturn } from '@/api/gates';
import { useTaskTransition } from '@/api/tasks';
import type { Task } from '@/types';

// ---------------------------------------------------------------------------
// Time-in-gate helper
// ---------------------------------------------------------------------------

function timeInGate(createdAt: string): string {
  const ms = Date.now() - new Date(createdAt).getTime();
  const mins = Math.floor(ms / 60_000);
  if (mins < 60) return `${mins}m`;
  const hrs = Math.floor(mins / 60);
  const remMins = mins % 60;
  if (hrs < 24) return `${hrs}h ${remMins}m`;
  const days = Math.floor(hrs / 24);
  return `${days}d ${hrs % 24}h`;
}

// ---------------------------------------------------------------------------
// Widget
// ---------------------------------------------------------------------------

export function GateQueueWidget() {
  const { data, isLoading } = useGateQueue();
  const tasks = data?.tasks ?? [];

  if (isLoading) {
    return (
      <div className="space-y-2">
        {[1, 2, 3].map((i) => (
          <div key={i} className="glass-panel h-14 animate-pulse" />
        ))}
      </div>
    );
  }

  if (tasks.length === 0) {
    return (
      <div className="flex items-center justify-center gap-2 py-8 text-glass-muted">
        <span className="w-2 h-2 rounded-full bg-status-active" />
        <span className="text-xs font-mono tracking-wider">Gate queue clear</span>
      </div>
    );
  }

  return (
    <div className="space-y-1.5">
      {tasks.map((task) => (
        <GateRow key={task.id} task={task} />
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Gate Row — single task in the queue
// ---------------------------------------------------------------------------

function GateRow({ task }: { task: Task }) {
  const [noteMode, setNoteMode] = useState<'fail' | 'return' | null>(null);
  const [note, setNote] = useState('');

  const approveGate = useGateApprove();
  const returnGate = useGateReturn();
  const transition = useTaskTransition();

  const isCritical = task.priority === 1;
  const isQA = task.status === 'QA_GATE';
  const isLevi = task.status === 'LEVI_GATE';
  const busy = approveGate.isPending || returnGate.isPending || transition.isPending;

  const handleApprove = useCallback(() => {
    if (isQA) {
      // QA_GATE → LEVI_GATE via task transition (qa-pass)
      transition.mutate({ taskId: task.id, action: 'qa-pass', body: { actor_id: 'AGT-001' } });
    } else {
      // LEVI_GATE → DEPLOYING via gate approve
      approveGate.mutate({ taskId: task.id });
    }
  }, [task.id, isQA, transition, approveGate]);

  const handleNoteSubmit = useCallback(() => {
    if (!note.trim()) return;
    if (noteMode === 'fail') {
      transition.mutate({
        taskId: task.id,
        action: 'qa-fail',
        body: { actor_id: 'AGT-001', note: note.trim() },
      });
    } else if (noteMode === 'return') {
      returnGate.mutate({ taskId: task.id, note: note.trim() });
    }
    setNote('');
    setNoteMode(null);
  }, [note, noteMode, task.id, transition, returnGate]);

  return (
    <div className={`
      glass-panel px-3 py-2.5 space-y-2
      ${isCritical ? 'animate-gate-ring border-status-gate/60' : ''}
    `}>
      {/* Main row */}
      <div className="flex items-center gap-2 min-w-0">
        {/* ZG-ref */}
        <span className="text-xs font-mono font-semibold text-gold shrink-0">
          {task.task_ref}
        </span>

        {/* Title */}
        <span className="text-sm text-glass-text truncate flex-1">
          {task.title}
        </span>

        {/* Gate badge */}
        <span className={`
          text-xxs font-mono px-1.5 py-0.5 rounded shrink-0
          ${isLevi
            ? 'bg-status-error/20 text-status-error animate-pulse'
            : 'bg-gold-muted text-gold'
          }
        `}>
          {task.status}
        </span>

        {/* Time in gate */}
        <span className="text-xxs font-mono text-glass-muted shrink-0">
          {timeInGate(task.created_at)}
        </span>
      </div>

      {/* Action buttons */}
      <div className="flex items-center gap-2">
        {/* Approve / Pass */}
        <button
          onClick={handleApprove}
          disabled={busy}
          className={`
            flex items-center gap-1.5 px-2.5 py-1 rounded-circuit text-xxs font-mono
            transition-all duration-200 disabled:opacity-30
            ${isLevi
              ? 'bg-gold/15 border border-gold/30 text-gold hover:bg-gold/25'
              : 'bg-status-active/10 border border-status-active/20 text-status-active hover:bg-status-active/20'
            }
          `}
        >
          {isLevi ? <ShieldCheck className="w-3 h-3" /> : <CheckCircle2 className="w-3 h-3" />}
          {isLevi ? 'APPROVE' : 'PASS'}
        </button>

        {/* Fail / Return */}
        <button
          onClick={() => setNoteMode(isQA ? 'fail' : 'return')}
          disabled={busy}
          className="
            flex items-center gap-1.5 px-2.5 py-1 rounded-circuit text-xxs font-mono
            bg-glass border border-glass-border text-glass-muted
            hover:border-status-error/30 hover:text-status-error
            transition-all duration-200 disabled:opacity-30
          "
        >
          {isQA ? <XCircle className="w-3 h-3" /> : <RotateCcw className="w-3 h-3" />}
          {isQA ? 'FAIL' : 'RETURN'}
        </button>
      </div>

      {/* Inline note textarea */}
      <AnimatePresence>
        {noteMode && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="overflow-hidden"
          >
            <div className="flex gap-2 pt-1">
              <textarea
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder={noteMode === 'fail' ? 'QA failure reason...' : 'Return reason...'}
                rows={2}
                autoFocus
                className="
                  flex-1 px-2.5 py-2 rounded-circuit text-xs font-mono
                  bg-obsidian border border-glass-border text-glass-text
                  placeholder:text-glass-muted/40
                  focus:outline-none focus:border-gold/30 resize-none
                "
              />
              <div className="flex flex-col gap-1">
                <button
                  onClick={handleNoteSubmit}
                  disabled={!note.trim() || busy}
                  className="
                    px-2 py-1.5 rounded-circuit
                    bg-status-error/15 border border-status-error/25 text-status-error
                    hover:bg-status-error/25 disabled:opacity-30
                    transition-all text-xxs font-mono
                  "
                >
                  <Send className="w-3 h-3" />
                </button>
                <button
                  onClick={() => { setNoteMode(null); setNote(''); }}
                  className="px-2 py-1.5 rounded-circuit text-xxs text-glass-muted hover:text-glass-text transition-colors"
                >
                  ✕
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
