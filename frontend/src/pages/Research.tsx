import { StatusBadge } from '@/components/common/StatusBadge';
import { MOCK_RESEARCH_REQUESTS } from '@/services/mockData';
import { formatTimestamp, cn } from '@/utils';
import type { StatusVariant } from '@/types';

const PRIORITY_STYLES: Record<string, string> = {
  high: 'border-l-accent-500',
  medium: 'border-l-warning',
  low: 'border-l-surface-500',
};

const STATUS_MAP: Record<string, StatusVariant> = {
  completed: 'healthy',
  in_progress: 'degraded',
  pending: 'pending',
  failed: 'error',
};

export function ResearchPage() {
  return (
    <div className="space-y-3">
      {MOCK_RESEARCH_REQUESTS.map((req) => (
        <div
          key={req.id}
          className={cn(
            'rounded-xl border border-surface-800 bg-surface-900 p-5 transition-colors hover:border-surface-700',
            'border-l-4',
            PRIORITY_STYLES[req.priority] ?? 'border-l-surface-700',
          )}
        >
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0 flex-1">
              <p className="font-medium text-surface-200">{req.query}</p>
              <div className="mt-2 flex flex-wrap items-center gap-3 text-xs text-surface-500">
                <span>Agent: {req.agentId}</span>
                <span>{formatTimestamp(req.createdAt)}</span>
                <span className={cn('font-medium', req.priority === 'high' ? 'text-error' : req.priority === 'medium' ? 'text-warning' : 'text-surface-400')}>
                  {req.priority}
                </span>
              </div>
            </div>
            <StatusBadge status={STATUS_MAP[req.status] ?? 'unknown'} label={req.status.replace('_', ' ')} />
          </div>
        </div>
      ))}
    </div>
  );
}
