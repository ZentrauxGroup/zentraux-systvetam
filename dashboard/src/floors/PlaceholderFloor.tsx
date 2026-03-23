/**
 * SYSTVETAM — Placeholder Floor
 * Zentraux Group LLC
 *
 * Rendered for floors not yet implemented.
 * Batch C-2+ will replace each with its department-native view.
 */

import { Construction } from 'lucide-react';
import type { FloorDefinition } from '@/design/tokens';

interface PlaceholderFloorProps {
  floor: FloorDefinition;
}

export function PlaceholderFloor({ floor }: PlaceholderFloorProps) {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-4 text-glass-muted">
      <Construction className="w-10 h-10 text-gold/30" />
      <h2 className="text-lg font-mono font-semibold tracking-wider text-glass-text">
        {floor.name}
      </h2>
      <p className="text-xs font-mono text-glass-muted">
        Department: {floor.department} — Batch C-2+
      </p>
    </div>
  );
}
