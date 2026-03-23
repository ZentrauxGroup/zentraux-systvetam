/**
 * SYSTVETAM — ZEN-CIRCUIT Design Tokens (TypeScript)
 * Zentraux Group LLC
 *
 * Typed export of all design tokens for use in components.
 * Tailwind handles CSS — these are for JS logic (animations,
 * conditional styling, status mapping, floor definitions).
 */

// ---------------------------------------------------------------------------
// Colors
// ---------------------------------------------------------------------------

export const colors = {
  gold: {
    DEFAULT: '#C9A84C',
    light: '#E8C97A',
    dark: '#8C6D2F',
    muted: 'rgba(201, 168, 76, 0.15)',
    pulse: 'rgba(201, 168, 76, 0.4)',
  },
  obsidian: {
    DEFAULT: '#0A0A0F',
    surface: '#12121A',
    panel: '#1A1A26',
    elevated: '#22222E',
  },
  glass: {
    DEFAULT: 'rgba(255, 255, 255, 0.04)',
    border: 'rgba(255, 255, 255, 0.08)',
    hover: 'rgba(255, 255, 255, 0.06)',
    text: 'rgba(248, 248, 240, 0.85)',
    muted: 'rgba(248, 248, 240, 0.45)',
  },
  status: {
    active: '#00FF88',
    idle: '#4A9EFF',
    executing: '#C9A84C',
    error: '#FF4444',
    offline: '#444455',
    gate: '#E8A030',
  },
} as const;

// ---------------------------------------------------------------------------
// Status → color mapping (crew pulse bar)
// ---------------------------------------------------------------------------

export type CrewStatusKey = 'ACTIVE' | 'IDLE' | 'EXECUTING' | 'ERROR' | 'OFFLINE';

export const statusColorMap: Record<CrewStatusKey, string> = {
  ACTIVE: colors.status.active,
  IDLE: colors.status.idle,
  EXECUTING: colors.status.executing,
  ERROR: colors.status.error,
  OFFLINE: colors.status.offline,
};

export const statusAnimationMap: Record<CrewStatusKey, string> = {
  ACTIVE: '',
  IDLE: '',
  EXECUTING: 'animate-pulse-gold',
  ERROR: 'animate-pulse-red',
  OFFLINE: 'opacity-30',
};

// ---------------------------------------------------------------------------
// Floor Definitions
// ---------------------------------------------------------------------------

export interface FloorDefinition {
  id: string;
  name: string;
  shortName: string;
  department: string;
  index: number;
}

export const FLOORS: FloorDefinition[] = [
  { id: 'lobby',        name: 'Lobby',           shortName: 'LBY', department: 'ALL',          index: 0 },
  { id: 'tower-suite',  name: 'Tower Suite',     shortName: 'TWR', department: 'HQ',           index: 1 },
  { id: 'intelligence', name: 'Intelligence',    shortName: 'INT', department: 'INTELLIGENCE',  index: 2 },
  { id: 'engineering',  name: 'Engineering',     shortName: 'ENG', department: 'ENGINEERING',    index: 3 },
  { id: 'gtm',          name: 'GTM Engine',      shortName: 'GTM', department: 'GTM',           index: 4 },
  { id: 'strategy',     name: 'Strategy',        shortName: 'STR', department: 'STRATEGY',      index: 5 },
  { id: 'finance',      name: 'Finance',         shortName: 'FIN', department: 'FINANCE',       index: 6 },
  { id: 'delivery',     name: 'Delivery',        shortName: 'DLV', department: 'DELIVERY',      index: 7 },
  { id: 'governance',   name: 'Governance',      shortName: 'GOV', department: 'GOVERNANCE',    index: 8 },
  { id: 'receipt-vault', name: 'Receipt Vault',  shortName: 'RCV', department: 'ALL',           index: 9 },
];

export const FLOOR_COUNT = FLOORS.length;

// ---------------------------------------------------------------------------
// Entry Sequence Timings
// ---------------------------------------------------------------------------

export const ENTRY_SEQUENCE = [
  { phase: 'void' as const,     duration: 400 },
  { phase: 'lotus' as const,    duration: 800 },
  { phase: 'wordmark' as const, duration: 600 },
  { phase: 'cut' as const,      duration: 0 },
  { phase: 'roster' as const,   duration: 800 },
  { phase: 'live' as const,     duration: 0 },
] as const;

// ---------------------------------------------------------------------------
// Timing Constants
// ---------------------------------------------------------------------------

export const TIMING = {
  ROSTER_STAGGER_MS: 40,
  WS_RECONNECT_BASE_MS: 1000,
  WS_RECONNECT_MAX_MS: 30000,
  WS_HEARTBEAT_TIMEOUT_MS: 90000,
  RECEIPT_FEED_MAX: 50,
  FLOOR_TRANSITION_MS: 300,
} as const;
