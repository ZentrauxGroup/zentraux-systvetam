/**
 * SYSTVETAM — Lobby Floor
 * Zentraux Group LLC
 *
 * The first thing you see. Command at a glance.
 *
 * - Hero: SYSTVETAM gold wordmark
 * - System status grid (Dispatch, PostgreSQL, Redis, WebSocket)
 * - Crew pulse strip (16 dots, colored by status)
 * - Active task count + gate count
 * - CTA: Enter Tower → TowerSuite
 */

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Activity, Database, Radio, Wifi, ChevronRight, Shield } from 'lucide-react';
import axios from 'axios';
import { useTowerStore } from '@/store';
import { statusColorMap, statusAnimationMap, type CrewStatusKey } from '@/design/tokens';
import type { StatusResponse, CrewListResponse, TaskListResponse } from '@/types';

export function Lobby() {
  const { setFloor, crewMembers, updateCrew, wsConnected } = useTowerStore();
  const [systemStatus, setSystemStatus] = useState<StatusResponse | null>(null);
  const [taskCount, setTaskCount] = useState(0);
  const [gateCount, setGateCount] = useState(0);
  const [loaded, setLoaded] = useState(false);

  // Fetch system status, crew, and task counts on mount
  useEffect(() => {
    const load = async () => {
      try {
        const [statusRes, crewRes, gateRes] = await Promise.allSettled([
          axios.get<StatusResponse>('/api/status'),
          axios.get<CrewListResponse>('/api/crew'),
          axios.get<TaskListResponse>('/api/gates/pending?limit=1'),
        ]);

        if (statusRes.status === 'fulfilled') setSystemStatus(statusRes.value.data);
        if (crewRes.status === 'fulfilled') {
          updateCrew(crewRes.value.data.crew);
          setTaskCount(crewRes.value.data.executing_count);
        }
        if (gateRes.status === 'fulfilled') setGateCount(gateRes.value.data.total);
      } catch {
        // Partial failure is fine — lobby still renders
      }
      setLoaded(true);
    };
    load();
  }, [updateCrew]);

  const checks = systemStatus?.checks;

  return (
    <div className="flex flex-col items-center justify-center h-full gap-8 max-w-lg mx-auto">
      {/* Hero Wordmark */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.2 }}
        className="text-center"
      >
        <h1 className="text-3xl md:text-4xl font-mono font-bold tracking-[0.3em] text-gold">
          SYSTVETAM
        </h1>
        <p className="text-xxs font-mono text-glass-muted mt-2 tracking-widest">
          ZENTRAUX GROUP LLC — CENTRAL DISPATCH
        </p>
      </motion.div>

      {/* System Status Grid */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: loaded ? 1 : 0 }}
        transition={{ duration: 0.4, delay: 0.4 }}
        className="grid grid-cols-2 gap-2 w-full"
      >
        <StatusCard
          label="Dispatch"
          icon={<Activity className="w-3.5 h-3.5" />}
          ok={systemStatus?.status === 'operational'}
          loaded={loaded}
        />
        <StatusCard
          label="PostgreSQL"
          icon={<Database className="w-3.5 h-3.5" />}
          ok={checks?.postgres === 'connected'}
          loaded={loaded}
        />
        <StatusCard
          label="Redis"
          icon={<Radio className="w-3.5 h-3.5" />}
          ok={checks?.redis === 'connected'}
          loaded={loaded}
        />
        <StatusCard
          label="WebSocket"
          icon={<Wifi className="w-3.5 h-3.5" />}
          ok={wsConnected}
          loaded={loaded}
        />
      </motion.div>

      {/* Crew Pulse Strip */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: loaded ? 1 : 0 }}
        transition={{ duration: 0.4, delay: 0.6 }}
        className="w-full"
      >
        <div className="flex items-center justify-between mb-2">
          <span className="text-xxs font-mono text-glass-muted tracking-wider">CREW ROSTER</span>
          <span className="text-xxs font-mono text-glass-muted">
            {crewMembers.length} OPERATORS
          </span>
        </div>
        <div className="flex gap-1.5 justify-center flex-wrap">
          {crewMembers.map((member, i) => {
            const statusKey = member.status as CrewStatusKey;
            return (
              <motion.div
                key={member.callsign}
                initial={{ opacity: 0, scale: 0.5 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.2, delay: 0.7 + i * 0.04 }}
                title={`${member.display_name} — ${member.status}`}
                className={`
                  w-3 h-3 rounded-full cursor-pointer transition-all
                  ${statusAnimationMap[statusKey] || ''}
                `}
                style={{ backgroundColor: statusColorMap[statusKey] ?? '#444455' }}
              />
            );
          })}
        </div>
      </motion.div>

      {/* Counts */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: loaded ? 1 : 0 }}
        transition={{ duration: 0.4, delay: 0.8 }}
        className="flex gap-6"
      >
        <div className="text-center">
          <span className="text-2xl font-mono font-bold text-gold">{taskCount}</span>
          <span className="block text-xxs font-mono text-glass-muted mt-0.5">EXECUTING</span>
        </div>
        <div className="text-center">
          <span className="text-2xl font-mono font-bold text-status-gate">{gateCount}</span>
          <span className="block text-xxs font-mono text-glass-muted mt-0.5">IN GATE</span>
        </div>
      </motion.div>

      {/* CTA */}
      <motion.button
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: loaded ? 1 : 0, y: loaded ? 0 : 10 }}
        transition={{ duration: 0.4, delay: 1.0 }}
        onClick={() => setFloor(1)}
        className="
          flex items-center gap-2 px-6 py-3 rounded-circuit
          bg-gold/10 border border-gold/30 text-gold
          hover:bg-gold/20 hover:border-gold/50
          transition-all duration-200 group
          font-mono text-sm tracking-wider
        "
      >
        <Shield className="w-4 h-4" />
        ENTER TOWER
        <ChevronRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
      </motion.button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Status Card — reusable grid cell
// ---------------------------------------------------------------------------

interface StatusCardProps {
  label: string;
  icon: React.ReactNode;
  ok: boolean | undefined;
  loaded: boolean;
}

function StatusCard({ label, icon, ok, loaded }: StatusCardProps) {
  const color = !loaded
    ? 'text-glass-muted'
    : ok
      ? 'text-status-active'
      : 'text-status-error';

  const dotColor = !loaded
    ? 'bg-glass-border'
    : ok
      ? 'bg-status-active'
      : 'bg-status-error';

  return (
    <div className="flex items-center gap-2.5 px-3 py-2.5 rounded-circuit bg-glass border border-glass-border">
      <span className={color}>{icon}</span>
      <span className="text-xs font-mono text-glass-text flex-1">{label}</span>
      <span className={`w-1.5 h-1.5 rounded-full ${dotColor}`} />
    </div>
  );
}
