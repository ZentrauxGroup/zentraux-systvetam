/**
 * SYSTVETAM — Tower Layout
 * Zentraux Group LLC
 *
 * Root layout: TopBar + FloorNav + FloorContent.
 * Keyboard navigation: ← → arrows switch floors.
 * Touch swipe navigation.
 * Floor transition via framer-motion AnimatePresence.
 *
 * Owns the floor component map directly.
 * Imports from @/floors/ (canonical location).
 */

import { useEffect, useCallback, useRef, type ReactElement } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { useTowerStore } from '@/store';
import { FLOORS, FLOOR_COUNT, TIMING } from '@/design/tokens';
import { TopBar } from './TopBar';
import { useWebSocket } from '@/hooks/useWebSocket';

// Floor components — canonical imports from @/floors/
import { Lobby } from '@/floors/Lobby';
import { TowerSuite } from '@/floors/TowerSuite';
import { Engineering } from '@/floors/Engineering';
import { Intelligence } from '@/floors/Intelligence';
import { GTM } from '@/floors/GTM';
import { Strategy } from '@/floors/Strategy';
import { Finance } from '@/floors/Finance';
import { Delivery } from '@/floors/Delivery';
import { Governance } from '@/floors/Governance';
import { ReceiptVault } from '@/floors/ReceiptVault';
import { PlaceholderFloor } from '@/floors/PlaceholderFloor';

// ---------------------------------------------------------------------------
// Floor index → component map
// ---------------------------------------------------------------------------

function getFloorComponent(index: number): ReactElement {
  switch (index) {
    case 0:
      return <Lobby />;
    case 1:
      return <TowerSuite />;
    case 2:
      return <Intelligence />;
    case 3:
      return <Engineering />;
    case 4:
      return <GTM />;
    case 5:
      return <Strategy />;
    case 6:
      return <Finance />;
    case 7:
      return <Delivery />;
    case 8:
      return <Governance />;
    case 9:
      return <ReceiptVault />;
    default:
      return <PlaceholderFloor floor={FLOORS[0]!} />;
  }
}

// ---------------------------------------------------------------------------
// Layout
// ---------------------------------------------------------------------------

export function TowerLayout() {
  const { currentFloor, setFloor } = useTowerStore();
  const touchStartX = useRef(0);
  const touchStartY = useRef(0);

  // Connect WebSocket at layout level
  useWebSocket();

  // Keyboard navigation
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      // Don't capture keystrokes when an input/textarea is focused
      const tag = (e.target as HTMLElement)?.tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;

      if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
        e.preventDefault();
        setFloor(Math.min(currentFloor + 1, FLOOR_COUNT - 1));
      } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
        e.preventDefault();
        setFloor(Math.max(currentFloor - 1, 0));
      } else if (e.key >= '0' && e.key <= '9') {
        const target = parseInt(e.key);
        if (target < FLOOR_COUNT) setFloor(target);
      }
    },
    [currentFloor, setFloor],
  );

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  // Touch swipe navigation
  const handleTouchStart = (e: React.TouchEvent) => {
    touchStartX.current = e.touches[0]!.clientX;
    touchStartY.current = e.touches[0]!.clientY;
  };

  const handleTouchEnd = (e: React.TouchEvent) => {
    const dx = e.changedTouches[0]!.clientX - touchStartX.current;
    const dy = e.changedTouches[0]!.clientY - touchStartY.current;

    // Only trigger on horizontal swipes > 50px that are more horizontal than vertical
    if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy) * 1.5) {
      if (dx < 0) {
        setFloor(Math.min(currentFloor + 1, FLOOR_COUNT - 1));
      } else {
        setFloor(Math.max(currentFloor - 1, 0));
      }
    }
  };

  const floor = FLOORS[currentFloor];

  return (
    <div
      className="h-screen w-screen bg-obsidian text-glass-text font-body overflow-hidden flex flex-col"
      onTouchStart={handleTouchStart}
      onTouchEnd={handleTouchEnd}
    >
      {/* Top Bar */}
      <TopBar floorName={floor?.name ?? 'Unknown'} />

      {/* Floor Navigation Dots */}
      <div className="flex justify-center gap-1.5 py-2">
        {FLOORS.map((f, i) => (
          <button
            key={f.id}
            onClick={() => setFloor(i)}
            className={`
              w-2 h-2 rounded-full transition-all duration-200
              ${i === currentFloor
                ? 'bg-gold w-5'
                : 'bg-glass-border hover:bg-glass-hover'
              }
            `}
            title={f.name}
            aria-label={`Navigate to ${f.name}`}
          />
        ))}
      </div>

      {/* Floor Content */}
      <main className="flex-1 overflow-y-auto overflow-x-hidden px-4 pb-4">
        <AnimatePresence mode="wait">
          <motion.div
            key={currentFloor}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            transition={{ duration: TIMING.FLOOR_TRANSITION_MS / 1000, ease: 'easeOut' }}
            className="h-full"
          >
            {getFloorComponent(currentFloor)}
          </motion.div>
        </AnimatePresence>
      </main>
    </div>
  );
}
