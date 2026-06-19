import { Bot, Activity } from 'lucide-react';

import { StatusBadge } from '@/components/common/StatusBadge';
import { MOCK_AGENTS } from '@/services/mockData';
import { formatTimestamp } from '@/utils';
import type { StatusVariant } from '@/types';

const STATUS_MAP: Record<string, StatusVariant> = {
  active: 'active',
  idle: 'inactive',
  error: 'error',
};

export function AgentsPage() {
  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2 xl:grid-cols-3">
      {MOCK_AGENTS.map((agent) => (
        <div
          key={agent.id}
          className="rounded-xl border border-surface-800 bg-surface-900 p-5 transition-all hover:border-surface-700"
        >
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent-600/10">
                <Bot className="h-5 w-5 text-accent-400" />
              </div>
              <div>
                <p className="font-medium text-surface-200">{agent.name}</p>
                <p className="text-xs text-surface-500">{agent.type}</p>
              </div>
            </div>
            <StatusBadge status={STATUS_MAP[agent.status] ?? 'unknown'} />
          </div>

          <div className="mt-4 flex items-center gap-4 text-xs text-surface-500">
            <span className="flex items-center gap-1">
              <Activity className="h-3.5 w-3.5" />
              {agent.taskCount} tasks
            </span>
            <span>Last active {formatTimestamp(agent.lastActive)}</span>
          </div>
        </div>
      ))}
    </div>
  );
}
