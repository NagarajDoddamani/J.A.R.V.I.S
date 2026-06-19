import { useQuery } from '@tanstack/react-query';

import { getMemories } from '@/api/memory';
import { queryKeys } from '@/constants/queryKeys';

export function useMemories(params?: Record<string, string>) {
  return useQuery({
    queryKey: queryKeys.memory.list(params),
    queryFn: () => getMemories(params),
    staleTime: 30000,
    retry: 2,
  });
}
