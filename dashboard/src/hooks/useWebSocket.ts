/**
 * SYSTVETAM — WebSocket Hook
 * Zentraux Group LLC
 *
 * Connects to ws://dispatch/ws. Parses JSON events from Redis relay.
 * Routes by event.channel to the correct store updater.
 * Auto-reconnect with exponential backoff (max 30s).
 * Heartbeat detection — marks disconnected if no message in 90s.
 */

import { useEffect, useRef, useCallback } from 'react';
import { useTowerStore } from '@/store';
import { TIMING } from '@/design/tokens';
import type { WsEvent, Receipt } from '@/types';

const WS_URL = `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}/ws`;

export function useWebSocket(): void {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptRef = useRef(0);
  const heartbeatTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const setWsStatus = useTowerStore((s) => s.setWsStatus);
  const pushEvent = useTowerStore((s) => s.pushEvent);
  const pushReceipt = useTowerStore((s) => s.pushReceipt);

  // Reset heartbeat timer on every message
  const resetHeartbeat = useCallback(() => {
    if (heartbeatTimerRef.current) clearTimeout(heartbeatTimerRef.current);
    heartbeatTimerRef.current = setTimeout(() => {
      setWsStatus(false);
    }, TIMING.WS_HEARTBEAT_TIMEOUT_MS);
  }, [setWsStatus]);

  // Route incoming events to store
  const handleMessage = useCallback(
    (data: string) => {
      try {
        const event: WsEvent = JSON.parse(data);
        pushEvent(event);
        resetHeartbeat();

        const channel = event.channel ?? '';

        switch (channel) {
          case 'task_events':
            // Task transitions — full refresh triggered by react-query invalidation
            break;

          case 'gate_events':
            // Gate decisions — invalidate gate query
            break;

          case 'receipts':
            if (event.receipt_ref && event.summary) {
              pushReceipt({
                id: crypto.randomUUID(),
                receipt_ref: event.receipt_ref as string,
                receipt_type: (event.receipt_type as string) ?? 'SYSTEM_EVENT',
                task_id: (event.task_ref as string) ?? null,
                crew_member_id: null,
                issued_by: 'SYSTEM',
                summary: event.summary as string,
                payload: null,
                sop_reference: (event.sop_reference as string) ?? null,
                created_at: event.ts,
              });
            }
            break;

          case 'crew_events':
            // Crew status changes — invalidate crew query
            break;

          case 'system_events':
            console.info('[SYSTVETAM]', event.event, event);
            break;

          default:
            // CONNECTED, HEARTBEAT, PONG — connection-level events
            if (event.event === 'CONNECTED') {
              console.info('[SYSTVETAM] WebSocket connected to Dispatch');
            }
            break;
        }
      } catch {
        // Non-JSON message — ignore
      }
    },
    [pushEvent, pushReceipt, resetHeartbeat],
  );

  // Connect
  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      setWsStatus(true);
      reconnectAttemptRef.current = 0;
      resetHeartbeat();
      console.info('[SYSTVETAM] WebSocket opened');
    };

    ws.onmessage = (e) => {
      handleMessage(e.data);
    };

    ws.onclose = () => {
      setWsStatus(false);
      scheduleReconnect();
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [setWsStatus, resetHeartbeat, handleMessage]);

  // Reconnect with exponential backoff
  const scheduleReconnect = useCallback(() => {
    const attempt = reconnectAttemptRef.current;
    const delay = Math.min(
      TIMING.WS_RECONNECT_BASE_MS * Math.pow(2, attempt),
      TIMING.WS_RECONNECT_MAX_MS,
    );
    reconnectAttemptRef.current = attempt + 1;

    console.info(`[SYSTVETAM] Reconnecting in ${delay}ms (attempt ${attempt + 1})`);
    reconnectTimerRef.current = setTimeout(connect, delay);
  }, [connect]);

  // Mount / unmount
  useEffect(() => {
    connect();

    return () => {
      if (heartbeatTimerRef.current) clearTimeout(heartbeatTimerRef.current);
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
      wsRef.current?.close();
    };
  }, [connect]);
}
