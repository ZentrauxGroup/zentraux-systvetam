/**
 * SYSTVETAM — Receipts API Hooks
 * Zentraux Group LLC
 *
 * React Query hook for the receipt vault — paginated, filterable.
 * Receipts are read-only from the API. No create/update mutations exist.
 * The receipt engine is the only writer. This is doctrine.
 */

import { useQuery } from '@tanstack/react-query';
import { client } from './client';
import type { Receipt } from '@/types';

interface ReceiptListResponse {
  receipts: Receipt[];
  total: number;
  offset: number;
  limit: number;
}

interface ReceiptFilters {
  receipt_type?: string;
  task_id?: string;
  offset?: number;
  limit?: number;
}

export function useReceiptVault(filters: ReceiptFilters = {}) {
  return useQuery<ReceiptListResponse>({
    queryKey: ['receipts', filters],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (filters.receipt_type) params.set('receipt_type', filters.receipt_type);
      if (filters.task_id) params.set('task_id', filters.task_id);
      params.set('offset', String(filters.offset ?? 0));
      params.set('limit', String(filters.limit ?? 50));
      const { data } = await client.get<ReceiptListResponse>(`/receipts?${params}`);
      return data;
    },
  });
}
