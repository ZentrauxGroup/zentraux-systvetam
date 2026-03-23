/**
 * SYSTVETAM — Crew API Hooks
 * Zentraux Group LLC
 *
 * React Query hooks for crew roster and detail.
 * Auto-refreshes every 30s to keep pulse bar live.
 */

import { useQuery } from '@tanstack/react-query';
import { client } from './client';
import type { CrewListResponse, CrewMember } from '@/types';

interface CrewMemberDetail extends CrewMember {
  active_tasks: import('@/types').Task[];
}

export function useCrewRoster(filters?: { status?: string; department?: string }) {
  return useQuery<CrewListResponse>({
    queryKey: ['crew', filters],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (filters?.status) params.set('status', filters.status);
      if (filters?.department) params.set('department', filters.department);
      const { data } = await client.get<CrewListResponse>(`/crew?${params}`);
      return data;
    },
    refetchInterval: 30_000,
  });
}

export function useCrewMember(callsign: string) {
  return useQuery<CrewMemberDetail>({
    queryKey: ['crew', callsign],
    queryFn: async () => {
      const { data } = await client.get<CrewMemberDetail>(`/crew/${callsign}`);
      return data;
    },
    enabled: !!callsign,
  });
}
