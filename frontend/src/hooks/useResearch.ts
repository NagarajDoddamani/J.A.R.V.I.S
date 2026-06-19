import { useQuery } from '@tanstack/react-query';

import { getResearchRequests } from '@/api/research';
import { queryKeys } from '@/constants/queryKeys';

export function useResearchRequests() {
  return useQuery({
    queryKey: queryKeys.research.list(),
    queryFn: getResearchRequests,
    staleTime: 30000,
    retry: 2,
  });
}
