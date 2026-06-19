import { apiClient } from '@/api/client';

import type { KnowledgeSource } from '@/types';

export function getKnowledgeSources(): Promise<KnowledgeSource[]> {
  return apiClient.get('/knowledge/sources').then((r) => r.data);
}
