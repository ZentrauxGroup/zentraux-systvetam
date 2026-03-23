/**
 * SYSTVETAM — Task API Hooks
 * Zentraux Group LLC
 *
 * React Query hooks for task CRUD and state transitions.
 * All transitions go through PATCH /tasks/{id}/{action}.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { client } from './client';
import type { Task, TaskListResponse } from '@/types';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface TaskFilters {
  status?: string;
  department?: string;
  assigned_to?: string;
  task_type?: string;
  priority?: number;
  offset?: number;
  limit?: number;
}

interface TaskCreateInput {
  title: string;
  description?: string;
  task_type?: string;
  department?: string;
  priority?: number;
  source?: string;
}

interface TransitionInput {
  taskId: string;
  action: string;
  body?: Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// Queries
// ---------------------------------------------------------------------------

export function useListTasks(filters: TaskFilters = {}) {
  return useQuery<TaskListResponse>({
    queryKey: ['tasks', filters],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (filters.status) params.set('status', filters.status);
      if (filters.department) params.set('department', filters.department);
      if (filters.assigned_to) params.set('assigned_to', filters.assigned_to);
      if (filters.task_type) params.set('task_type', filters.task_type);
      if (filters.priority !== undefined) params.set('priority', String(filters.priority));
      params.set('offset', String(filters.offset ?? 0));
      params.set('limit', String(filters.limit ?? 100));
      const { data } = await client.get<TaskListResponse>(`/tasks?${params}`);
      return data;
    },
  });
}

// ---------------------------------------------------------------------------
// Mutations
// ---------------------------------------------------------------------------

export function useCreateTask() {
  const qc = useQueryClient();
  return useMutation<Task, Error, TaskCreateInput>({
    mutationFn: async (input) => {
      const { data } = await client.post<Task>('/tasks', input);
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['tasks'] });
    },
  });
}

export function useTaskTransition() {
  const qc = useQueryClient();
  return useMutation<Task, Error, TransitionInput>({
    mutationFn: async ({ taskId, action, body }) => {
      const { data } = await client.patch<Task>(`/tasks/${taskId}/${action}`, body ?? {});
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['tasks'] });
      qc.invalidateQueries({ queryKey: ['gates'] });
    },
  });
}
