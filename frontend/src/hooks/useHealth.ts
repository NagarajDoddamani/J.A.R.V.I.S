import { useQuery } from '@tanstack/react-query';

import { getHealthStatus } from '@/api/health';
import { queryKeys } from '@/constants/queryKeys';
import { POLL_INTERVALS } from '@/constants';

export function useHealth() {
  return useQuery({
    queryKey: queryKeys.health.status(),
    queryFn: getHealthStatus,
    refetchInterval: POLL_INTERVALS.STATUS,
    staleTime: POLL_INTERVALS.STATUS / 2,
    retry: 2,
  });
}
