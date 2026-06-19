import { useQuery } from '@tanstack/react-query';

import { getKnowledgeSources } from '@/api/knowledge';
import { queryKeys } from '@/constants/queryKeys';

export function useKnowledgeSources() {
  return useQuery({
    queryKey: queryKeys.knowledge.list(),
    queryFn: getKnowledgeSources,
    staleTime: 30000,
    retry: 2,
  });
}
