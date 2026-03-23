/**
 * SYSTVETAM — Receipt Feed
 * Zentraux Group LLC
 *
 * Live receipt feed from WebSocket → Zustand store.
 * Newest at top. Last 50 entries. New items animate in.
 * Badge colors by receipt type category.
 */

import { motion, AnimatePresence } from 'framer-motion';
import { FileText, Archive } from 'lucide-react';
import { useTowerStore } from '@/store';
import type { Receipt } from '@/types';

// ---------------------------------------------------------------------------
// Receipt type → badge styling
// ---------------------------------------------------------------------------

type BadgeStyle = { bg: string; text: string };

const BADGE_MAP: Record<string, BadgeStyle> = {
  TASK_CREATED:    { bg: 'bg-status-idle/20',   text: 'text-status-idle' },
  TASK_ASSIGNED:   { bg: 'bg-status-idle/20',   text: 'text-status-idle' },
  CREW_ACTIVATED:  { bg: 'bg-gold-muted',       text: 'text-gold' },
  QA_EVALUATION:   { bg: 'bg-gold-muted',       text: 'text-gold' },
  QA_PASSED:       { bg: 'bg-gold-muted',       text: 'text-gold' },
  QA_FAILED:       { bg: 'bg-status-error/20',  text: 'text-status-error' },
  GATE_APPROVED:   { bg: 'bg-gold-muted',       text: 'text-gold' },
  GATE_RETURNED:   { bg: 'bg-status-gate/20',   text: 'text-status-gate' },
  TASK_COMPLETE:   { bg: 'bg-status-active/15', text: 'text-status-active' },
  TASK_RECEIPTED:  { bg: 'bg-status-active/10', text: 'text-status-active' },
  ERROR_LOGGED:    { bg: 'bg-status-error/20',  text: 'text-status-error' },
};

const DEFAULT_BADGE: BadgeStyle = { bg: 'bg-glass', text: 'text-glass-muted' };

// ---------------------------------------------------------------------------
// Relative time helper
// ---------------------------------------------------------------------------

function relativeTime(ts: string): string {
  const diff = Date.now() - new Date(ts).getTime();
  const secs = Math.floor(diff / 1000);
  if (secs < 60) return `${secs}s ago`;
  const mins = Math.floor(secs / 60);
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

// ---------------------------------------------------------------------------
// Feed
// ---------------------------------------------------------------------------

export function ReceiptFeed() {
  const receiptFeed = useTowerStore((s) => s.receiptFeed);

  if (receiptFeed.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-8 gap-2 text-glass-muted">
        <Archive className="w-5 h-5 text-glass-muted/40" />
        <span className="text-xs font-mono tracking-wider">
          Vault silent — awaiting receipts
        </span>
      </div>
    );
  }

  return (
    <div className="space-y-1 overflow-y-auto max-h-[calc(100vh-320px)] scrollbar-none">
      <AnimatePresence initial={false}>
        {receiptFeed.map((receipt) => (
          <ReceiptEntry key={receipt.receipt_ref + receipt.created_at} receipt={receipt} />
        ))}
      </AnimatePresence>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Single receipt entry
// ---------------------------------------------------------------------------

function ReceiptEntry({ receipt }: { receipt: Receipt }) {
  const badge = BADGE_MAP[receipt.receipt_type] ?? DEFAULT_BADGE;

  return (
    <motion.div
      initial={{ opacity: 0, y: -8, height: 0 }}
      animate={{ opacity: 1, y: 0, height: 'auto' }}
      exit={{ opacity: 0, height: 0 }}
      transition={{ duration: 0.2 }}
      className="glass-panel px-2.5 py-2 overflow-hidden"
    >
      <div className="flex items-start gap-2 min-w-0">
        <FileText className="w-3 h-3 text-gold/40 mt-0.5 shrink-0" />

        <div className="flex-1 min-w-0">
          {/* Ref + badge + time */}
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="text-xxs font-mono font-semibold text-gold truncate">
              {receipt.receipt_ref}
            </span>
            <span className={`text-[9px] font-mono px-1 py-px rounded ${badge.bg} ${badge.text}`}>
              {receipt.receipt_type}
            </span>
            <span className="text-[9px] font-mono text-glass-muted/50 ml-auto shrink-0">
              {relativeTime(receipt.created_at)}
            </span>
          </div>

          {/* Summary */}
          <p className="text-xxs text-glass-muted mt-0.5 leading-relaxed truncate">
            {receipt.summary}
          </p>
        </div>
      </div>
    </motion.div>
  );
}
