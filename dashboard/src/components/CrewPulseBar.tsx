/**
 * SYSTVETAM — Crew Pulse Bar
 * Zentraux Group LLC
 *
 * Horizontal strip — all 16 crew, status dot + callsign.
 * Tooltip on hover. 48px max height. Auto-refresh 30s.
 * Designed to sit in TowerSuite header area.
 */

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useCrewRoster } from '@/api/crew';
import { statusColorMap, statusAnimationMap, type CrewStatusKey } from '@/design/tokens';
import type { CrewMember } from '@/types';

export function CrewPulseBar() {
  const { data, isLoading } = useCrewRoster();
  const crew = data?.crew ?? [];

  if (isLoading) {
    return (
      <div className="flex gap-1.5 h-12 items-center overflow-x-auto px-1">
        {Array.from({ length: 16 }).map((_, i) => (
          <div key={i} className="w-6 h-6 rounded-full bg-glass-border animate-pulse shrink-0" />
        ))}
      </div>
    );
  }

  return (
    <div className="flex gap-1 h-12 items-center overflow-x-auto px-1 scrollbar-none">
      {crew.map((member) => (
        <CrewDot key={member.callsign} member={member} />
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Individual crew dot with tooltip
// ---------------------------------------------------------------------------

function CrewDot({ member }: { member: CrewMember }) {
  const [hovered, setHovered] = useState(false);
  const statusKey = member.status as CrewStatusKey;
  const color = statusColorMap[statusKey] ?? '#444455';
  const animation = statusAnimationMap[statusKey] ?? '';

  // Short callsign: "marcus-reed" → "marcus"
  const shortName = member.callsign.split('-')[0] ?? member.callsign;

  return (
    <div
      className="relative flex flex-col items-center shrink-0 cursor-default"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      {/* Status dot */}
      <div
        className={`w-3.5 h-3.5 rounded-full ${animation}`}
        style={{ backgroundColor: color }}
      />

      {/* Callsign */}
      <span className="text-[8px] font-mono text-glass-muted mt-0.5 leading-none w-9 text-center truncate">
        {shortName}
      </span>

      {/* Tooltip */}
      <AnimatePresence>
        {hovered && (
          <motion.div
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 4 }}
            transition={{ duration: 0.12 }}
            className="
              absolute bottom-full mb-2 z-30
              bg-obsidian-elevated border border-glass-border rounded-circuit
              px-3 py-2 shadow-glass whitespace-nowrap
              pointer-events-none
            "
          >
            <div className="text-xs font-mono font-semibold text-glass-text">
              {member.display_name}
            </div>
            <div className="text-xxs font-mono text-glass-muted mt-0.5">
              {member.role}
            </div>
            <div className="text-xxs font-mono text-glass-muted">
              {member.department}
            </div>
            <div className="text-xxs font-mono mt-1" style={{ color }}>
              {member.current_task_ref
                ? `→ ${member.current_task_ref}`
                : 'Idle'
              }
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
