import { apiClient } from '@/api/client';

import type { ResearchRequest } from '@/types';

export function getResearchRequests(): Promise<ResearchRequest[]> {
  return apiClient.get('/research/requests').then((r) => r.data);
}
