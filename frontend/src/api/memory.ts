import { apiClient } from '@/api/client';

import type { MemoryItem, PaginatedResponse } from '@/types';

export function getMemories(params?: Record<string, string>): Promise<PaginatedResponse<MemoryItem>> {
  return apiClient.get('/memory', { params }).then((r) => r.data);
}

export function getMemoryById(id: string): Promise<MemoryItem> {
  return apiClient.get(`/memory/${id}`).then((r) => r.data);
}
