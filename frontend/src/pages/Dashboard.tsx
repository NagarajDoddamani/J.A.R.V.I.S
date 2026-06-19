import { MetricCard } from '@/components/common/MetricCard';
import { StatusBadge } from '@/components/common/StatusBadge';
import { MOCK_METRICS, MOCK_SERVICES } from '@/services/mockData';

export function DashboardPage() {
  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-sm font-medium uppercase tracking-wider text-surface-400">Overview</h2>
        <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
          {MOCK_METRICS.map((metric) => (
            <MetricCard key={metric.label} metric={metric} />
          ))}
        </div>
      </div>

      <div>
        <h2 className="text-sm font-medium uppercase tracking-wider text-surface-400">Infrastructure</h2>
        <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
          {MOCK_SERVICES.map((svc) => (
            <div
              key={svc.name}
              className="flex items-center justify-between rounded-xl border border-surface-800 bg-surface-900/60 px-5 py-4 backdrop-blur-xl transition-all duration-200 hover:border-surface-700 hover:bg-surface-800/80 ring-1 ring-surface-800/50"
            >
              <div>
                <p className="text-sm font-medium text-surface-200">{svc.name}</p>
                <p className="mt-0.5 text-xs text-surface-500">{svc.latency}ms</p>
              </div>
              <StatusBadge status={svc.status} />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
