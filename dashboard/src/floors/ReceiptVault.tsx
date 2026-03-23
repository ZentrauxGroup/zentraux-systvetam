/**
 * SYSTVETAM — Receipt Vault Floor
 * Zentraux Group LLC
 *
 * Floor index 9. The permanent record.
 * Read-only. Append-only. No mutations. No edits. No deletes.
 * The vault is sacred. It only displays.
 *
 * "No Receipt = No Done" — L0 Doctrine
 */

import { useState, useMemo, useCallback, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Archive, Search, X, Download, Check } from 'lucide-react';
import { useReceiptVault } from '@/api/receipts';
import type { Receipt } from '@/types';

// ---------------------------------------------------------------------------
// Filter types
// ---------------------------------------------------------------------------

type TimeFilter = 'all' | 'today' | 'week' | 'month';

const TIME_TABS: { key: TimeFilter; label: string }[] = [
  { key: 'all',   label: 'ALL' },
  { key: 'today', label: 'TODAY' },
  { key: 'week',  label: 'THIS WEEK' },
  { key: 'month', label: 'THIS MONTH' },
];

// ---------------------------------------------------------------------------
// Badge colors by receipt type category
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
// Helpers
// ---------------------------------------------------------------------------

function formatTimestamp(ts: string): string {
  const d = new Date(ts);
  return d.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: true,
    timeZone: 'America/Phoenix',
  });
}

function startOfToday(): Date {
  const d = new Date();
  d.setHours(0, 0, 0, 0);
  return d;
}

function startOfWeek(): Date {
  const d = startOfToday();
  d.setDate(d.getDate() - d.getDay());
  return d;
}

function startOfMonth(): Date {
  const d = startOfToday();
  d.setDate(1);
  return d;
}

// ---------------------------------------------------------------------------
// Toast (export placeholder)
// ---------------------------------------------------------------------------

function ExportToast({ onDismiss }: { onDismiss: () => void }) {
  useEffect(() => {
    const t = setTimeout(onDismiss, 4000);
    return () => clearTimeout(t);
  }, [onDismiss]);

  return (
    <motion.div
      initial={{ opacity: 0, y: -10, x: 10 }}
      animate={{ opacity: 1, y: 0, x: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="
        fixed top-4 right-4 z-[60]
        flex items-center gap-2 px-4 py-2.5 rounded-circuit
        bg-obsidian-elevated border border-gold/30
        shadow-gold-glow max-w-sm
      "
    >
      <Check className="w-3.5 h-3.5 text-gold shrink-0" />
      <span className="text-xs font-mono text-gold">
        PDF export available in Sprint 4 — vault integrity maintained
      </span>
    </motion.div>
  );
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function ReceiptVault() {
  const [timeFilter, setTimeFilter] = useState<TimeFilter>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [showToast, setShowToast] = useState(false);

  const { data, isLoading } = useReceiptVault({ limit: 200 });
  const receipts = data?.receipts ?? [];
  const totalCount = data?.total ?? 0;

  // Apply client-side filters
  const filtered = useMemo(() => {
    let result = receipts;

    // Time filter
    if (timeFilter !== 'all') {
      const cutoff = timeFilter === 'today'
        ? startOfToday()
        : timeFilter === 'week'
          ? startOfWeek()
          : startOfMonth();

      result = result.filter((r) => new Date(r.created_at) >= cutoff);
    }

    // Search filter
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      result = result.filter((r) =>
        r.receipt_ref.toLowerCase().includes(q) ||
        r.summary.toLowerCase().includes(q) ||
        r.issued_by.toLowerCase().includes(q) ||
        (r.sop_reference ?? '').toLowerCase().includes(q)
      );
    }

    return result;
  }, [receipts, timeFilter, searchQuery]);

  const clearFilters = useCallback(() => {
    setTimeFilter('all');
    setSearchQuery('');
  }, []);

  // Determine empty state type
  const hasAnyReceipts = receipts.length > 0;
  const hasFilterResults = filtered.length > 0;

  return (
    <div className="h-full flex flex-col gap-3">
      {/* Toast */}
      <AnimatePresence>
        {showToast && <ExportToast onDismiss={() => setShowToast(false)} />}
      </AnimatePresence>

      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h2 className="text-sm font-mono font-semibold tracking-[0.15em] text-gold">
            RECEIPT VAULT
          </h2>
          <p className="text-[10px] font-mono text-glass-muted/60 mt-0.5 tracking-wider">
            IMMUTABLE RECORD — APPEND ONLY
          </p>
        </div>
        <span className="text-xxs font-mono px-2 py-0.5 rounded bg-gold-muted text-gold">
          {totalCount} RECEIPTS FILED
        </span>
      </div>

      {/* Filter + Search Bar */}
      <div className="flex items-center gap-3 flex-wrap">
        {/* Time tabs */}
        <div className="flex gap-1">
          {TIME_TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setTimeFilter(tab.key)}
              className={`
                px-2 py-1 rounded-circuit text-xxs font-mono tracking-wider
                transition-all duration-150
                ${timeFilter === tab.key
                  ? 'bg-gold/15 text-gold border border-gold/25'
                  : 'text-glass-muted hover:text-glass-text border border-transparent'
                }
              `}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Search input */}
        <div className="flex-1 min-w-[180px] relative">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-glass-muted/40" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search ref, summary, agent..."
            className="field-input pl-8 pr-8 py-1.5 text-xs"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-glass-muted hover:text-glass-text transition-colors"
            >
              <X className="w-3 h-3" />
            </button>
          )}
        </div>
      </div>

      {/* Receipt List */}
      <div className="flex-1 overflow-y-auto scrollbar-none min-h-0">
        {isLoading ? (
          <LoadingSkeleton />
        ) : !hasAnyReceipts ? (
          <EmptyVault />
        ) : !hasFilterResults ? (
          <NoResults onClear={clearFilters} />
        ) : (
          <div className="space-y-0">
            {filtered.map((receipt) => (
              <ReceiptRow key={receipt.id} receipt={receipt} />
            ))}
          </div>
        )}
      </div>

      {/* Export Button */}
      <div className="flex justify-end pt-1">
        <button
          onClick={() => setShowToast(true)}
          className="
            flex items-center gap-1.5 px-3 py-1.5 rounded-circuit
            bg-gold/10 border border-gold/30 text-gold
            hover:bg-gold/20 hover:border-gold/50
            transition-all duration-200
            text-xxs font-mono tracking-wider
          "
        >
          <Download className="w-3 h-3" />
          EXPORT VAULT
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Receipt Row — single immutable record
// ---------------------------------------------------------------------------

function ReceiptRow({ receipt }: { receipt: Receipt }) {
  const badge = BADGE_MAP[receipt.receipt_type] ?? DEFAULT_BADGE;

  return (
    <div className="glass-panel border-b border-white/5 px-3 py-2.5 rounded-none first:rounded-t-circuit last:rounded-b-circuit">
      {/* Main row */}
      <div className="flex items-center gap-2 flex-wrap min-w-0">
        {/* Receipt ref — the anchor */}
        <span className="text-xs font-mono font-semibold text-gold tracking-wide shrink-0">
          {receipt.receipt_ref}
        </span>

        {/* Type badge */}
        <span className={`text-[9px] font-mono px-1.5 py-0.5 rounded shrink-0 ${badge.bg} ${badge.text}`}>
          {receipt.receipt_type}
        </span>

        {/* SOP reference as department-like badge */}
        {receipt.sop_reference && (
          <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-glass text-glass-muted shrink-0">
            {receipt.sop_reference}
          </span>
        )}

        <span className="text-glass-muted/30">·</span>

        {/* Issued by */}
        <span className="text-sm text-glass-text truncate">
          {receipt.issued_by}
        </span>

        {/* Task ref if present */}
        {receipt.task_id && (
          <>
            <span className="text-glass-muted/30">·</span>
            <span className="text-xxs font-mono text-glass-muted shrink-0">
              {receipt.task_id.slice(0, 8)}
            </span>
          </>
        )}

        {/* Timestamp — right aligned */}
        <span className="text-xxs font-mono text-glass-muted/50 ml-auto shrink-0">
          {formatTimestamp(receipt.created_at)}
        </span>
      </div>

      {/* Summary — full text, no truncation */}
      <p className="text-sm text-glass-muted mt-1.5 ml-0 leading-relaxed">
        {receipt.summary}
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Empty states
// ---------------------------------------------------------------------------

function EmptyVault() {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-3 text-glass-muted">
      <Archive className="w-10 h-10 text-gold/20" />
      <span className="text-sm font-mono tracking-wider text-glass-text">
        The vault is silent
      </span>
      <span className="text-xs font-mono text-glass-muted/60">
        No receipts filed
      </span>
    </div>
  );
}

function NoResults({ onClear }: { onClear: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-3 text-glass-muted">
      <Search className="w-8 h-8 text-glass-muted/20" />
      <span className="text-sm font-mono tracking-wider text-glass-text">
        No receipts match
      </span>
      <button
        onClick={onClear}
        className="text-xs font-mono text-gold hover:text-gold-light transition-colors underline underline-offset-2"
      >
        Clear filters
      </button>
    </div>
  );
}

function LoadingSkeleton() {
  const widths = [180, 220, 160, 200, 190, 240, 170, 210];
  return (
    <div className="space-y-0">
      {widths.map((w, i) => (
        <div
          key={i}
          className="glass-panel border-b border-white/5 px-3 py-3 rounded-none first:rounded-t-circuit last:rounded-b-circuit"
        >
          <div className="flex items-center gap-3">
            <div className="h-3 rounded bg-gold-muted/30 animate-pulse" style={{ width: w }} />
            <div className="h-3 w-16 rounded bg-glass-border animate-pulse" />
            <div className="h-3 flex-1 rounded bg-glass-border/50 animate-pulse" />
          </div>
          <div className="h-3 w-3/4 rounded bg-glass-border/30 animate-pulse mt-2" />
        </div>
      ))}
    </div>
  );
}
