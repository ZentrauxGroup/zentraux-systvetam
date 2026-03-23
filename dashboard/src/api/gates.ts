/**
 * SYSTVETAM — Gate API Hooks
 * Zentraux Group LLC
 *
 * React Query hooks for the gate approval queue.
 * Auto-refreshes every 10s — gold rings must surface fast.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { client } from './client';
import type { Task, TaskListResponse } from '@/types';

interface GateActionInput {
  taskId: string;
  actor_id?: string;
  note?: string;
}

export function useGateQueue() {
  return useQuery<TaskListResponse>({
    queryKey: ['gates', 'pending'],
    queryFn: async () => {
      const { data } = await client.get<TaskListResponse>('/gates/pending');
      return data;
    },
    refetchInterval: 10_000,
  });
}

export function useGateApprove() {
  const qc = useQueryClient();
  return useMutation<Task, Error, GateActionInput>({
    mutationFn: async ({ taskId, actor_id, note }) => {
      const { data } = await client.post<Task>(`/gates/${taskId}/approve`, {
        actor_id: actor_id ?? 'AGT-001',
        note,
      });
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['gates'] });
      qc.invalidateQueries({ queryKey: ['tasks'] });
    },
  });
}

export function useGateReturn() {
  const qc = useQueryClient();
  return useMutation<Task, Error, GateActionInput>({
    mutationFn: async ({ taskId, actor_id, note }) => {
      const { data } = await client.post<Task>(`/gates/${taskId}/return`, {
        actor_id: actor_id ?? 'AGT-001',
        note,
      });
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['gates'] });
      qc.invalidateQueries({ queryKey: ['tasks'] });
    },
  });
}
