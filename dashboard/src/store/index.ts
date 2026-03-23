/**
 * SYSTVETAM — Global Store
 * Zentraux Group LLC
 *
 * Zustand store. Single source of truth for Tower Dashboard state.
 * WebSocket events, auth state, crew roster, gate queue, receipt feed.
 */

import { create } from 'zustand';
import type { AuthUser, CrewMember, Task, Receipt, WsEvent } from '@/types';
import { TIMING } from '@/design/tokens';

// ---------------------------------------------------------------------------
// State Shape
// ---------------------------------------------------------------------------

interface TowerState {
  // Floor navigation
  currentFloor: number;
  setFloor: (index: number) => void;

  // Auth
  authToken: string | null;
  currentUser: AuthUser | null;
  setAuth: (token: string, user: AuthUser) => void;
  clearAuth: () => void;

  // Crew
  crewMembers: CrewMember[];
  updateCrew: (crew: CrewMember[]) => void;
  updateCrewMember: (callsign: string, partial: Partial<CrewMember>) => void;

  // Tasks
  activeTasks: Task[];
  updateTasks: (tasks: Task[]) => void;

  // Gate queue (tasks in QA_GATE or LEVI_GATE)
  gateQueue: Task[];
  updateGateQueue: (tasks: Task[]) => void;

  // Receipt feed (last N)
  receiptFeed: Receipt[];
  pushReceipt: (receipt: Receipt) => void;

  // WebSocket status
  wsConnected: boolean;
  wsLastEvent: WsEvent | null;
  setWsStatus: (connected: boolean) => void;
  pushEvent: (event: WsEvent) => void;
}

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

export const useTowerStore = create<TowerState>((set) => ({
  // --- Floor ---
  currentFloor: 0,
  setFloor: (index) => set({ currentFloor: index }),

  // --- Auth ---
  authToken: localStorage.getItem('systvetam_token'),
  currentUser: null,
  setAuth: (token, user) => {
    localStorage.setItem('systvetam_token', token);
    set({ authToken: token, currentUser: user });
  },
  clearAuth: () => {
    localStorage.removeItem('systvetam_token');
    set({ authToken: null, currentUser: null });
  },

  // --- Crew ---
  crewMembers: [],
  updateCrew: (crew) => set({ crewMembers: crew }),
  updateCrewMember: (callsign, partial) =>
    set((state) => ({
      crewMembers: state.crewMembers.map((c) =>
        c.callsign === callsign ? { ...c, ...partial } : c,
      ),
    })),

  // --- Tasks ---
  activeTasks: [],
  updateTasks: (tasks) => set({ activeTasks: tasks }),

  // --- Gate Queue ---
  gateQueue: [],
  updateGateQueue: (tasks) => set({ gateQueue: tasks }),

  // --- Receipt Feed ---
  receiptFeed: [],
  pushReceipt: (receipt) =>
    set((state) => ({
      receiptFeed: [receipt, ...state.receiptFeed].slice(0, TIMING.RECEIPT_FEED_MAX),
    })),

  // --- WebSocket ---
  wsConnected: false,
  wsLastEvent: null,
  setWsStatus: (connected) => set({ wsConnected: connected }),
  pushEvent: (event) => set({ wsLastEvent: event }),
}));
