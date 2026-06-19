import { useState } from 'react';
import { Search, RotateCcw } from 'lucide-react';

import { StatusBadge } from '@/components/common/StatusBadge';
import { MOCK_MEMORIES } from '@/services/mockData';
import { formatTimestamp, cn, truncate } from '@/utils';

export function MemoryPage() {
  const [search, setSearch] = useState('');

  const filtered = MOCK_MEMORIES.filter(
    (m) =>
      m.content.toLowerCase().includes(search.toLowerCase()) ||
      m.category.toLowerCase().includes(search.toLowerCase()),
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-surface-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search memories..."
            className={cn(
              'w-full rounded-xl border border-surface-700 bg-surface-900 py-2.5 pl-10 pr-4 text-sm text-surface-200',
              'placeholder:text-surface-500',
              'focus:border-accent-500 focus:outline-none focus:ring-1 focus:ring-accent-500',
            )}
          />
        </div>
        <button
          type="button"
          className="flex items-center gap-2 rounded-xl border border-surface-700 bg-surface-900 px-4 py-2.5 text-sm text-surface-300 transition-colors hover:bg-surface-800"
        >
          <RotateCcw className="h-4 w-4" />
          Refresh
        </button>
      </div>

      <div className="space-y-2">
        {filtered.map((mem) => (
          <div
            key={mem.id}
            className="rounded-xl border border-surface-800 bg-surface-900 p-4 transition-colors hover:border-surface-700"
          >
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0 flex-1">
                <p className="text-sm text-surface-200">{truncate(mem.content, 200)}</p>
                <p className="mt-1.5 text-xs text-surface-500">
                  {formatTimestamp(mem.timestamp)} &middot; Source: {mem.source}
                </p>
              </div>
              <StatusBadge status={mem.category as 'active'} label={mem.category} size="sm" />
            </div>
          </div>
        ))}
        {filtered.length === 0 && (
          <p className="py-12 text-center text-sm text-surface-500">No memories found.</p>
        )}
      </div>
    </div>
  );
}
