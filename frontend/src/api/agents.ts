import { apiClient } from '@/api/client';

import type { Agent } from '@/types';

export function getAgents(): Promise<Agent[]> {
  return apiClient.get('/agents').then((r) => r.data);
}
