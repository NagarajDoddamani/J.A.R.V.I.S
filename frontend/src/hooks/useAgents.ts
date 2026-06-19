import { useQuery } from '@tanstack/react-query';

import { getAgents } from '@/api/agents';
import { queryKeys } from '@/constants/queryKeys';

export function useAgents() {
  return useQuery({
    queryKey: queryKeys.agents.list(),
    queryFn: getAgents,
    staleTime: 30000,
    retry: 2,
  });
}
