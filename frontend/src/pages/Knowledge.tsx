import { FileText, Globe } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

import { StatusBadge } from '@/components/common/StatusBadge';
import { MOCK_KNOWLEDGE_SOURCES } from '@/services/mockData';
import { formatTimestamp } from '@/utils';

const TYPE_ICONS: Record<string, LucideIcon> = {
  file: FileText,
  url: Globe,
};

export function KnowledgePage() {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {MOCK_KNOWLEDGE_SOURCES.map((src) => {
          const Icon = TYPE_ICONS[src.type] ?? FileText;
          return (
            <div
              key={src.id}
              className="group rounded-xl border border-surface-800 bg-surface-900 p-5 transition-all hover:border-surface-700"
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent-600/10">
                    <Icon className="h-5 w-5 text-accent-400" />
                  </div>
                  <div>
                    <p className="font-medium text-surface-200">{src.name}</p>
                    <p className="text-xs text-surface-500">{src.type.toUpperCase()}</p>
                  </div>
                </div>
                <StatusBadge status={src.status as 'active'} />
              </div>

              <div className="mt-4 flex items-center gap-4 text-xs text-surface-500">
                <span>
                  <strong className="text-surface-300">{src.documentCount}</strong> documents
                </span>
                <span>Last ingested {formatTimestamp(src.lastIngested)}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
