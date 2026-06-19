import { apiClient } from '@/api/client';

import type { ServiceStatus } from '@/types';

export interface HealthResponse {
  status: string;
  services: ServiceStatus[];
}

export function getHealthStatus(): Promise<HealthResponse> {
  return apiClient.get('/health').then((r) => r.data);
}
