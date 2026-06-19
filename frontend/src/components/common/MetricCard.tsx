import { cn } from '@/utils';
import type { MetricData } from '@/types';
import * as Icons from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

interface MetricCardProps {
  metric: MetricData;
  onClick?: () => void;
}

export function MetricCard({ metric, onClick }: MetricCardProps) {
  const IconComponent = (Icons as unknown as Record<string, LucideIcon>)[metric.icon] ?? Icons.BarChart3;
  const hasChange = metric.change !== undefined;

  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'flex flex-col gap-3 rounded-xl border border-surface-800 bg-surface-900/60 p-5 text-left backdrop-blur-xl transition-all duration-200',
        'hover:border-accent-600/50 hover:bg-surface-800/80 hover:shadow-lg hover:shadow-accent-900/10',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-500',
        'ring-1 ring-surface-800/50',
        onClick ? 'cursor-pointer' : 'cursor-default',
      )}
      aria-label={`${metric.label}: ${metric.value}`}
    >
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-surface-400">{metric.label}</span>
        <IconComponent className="h-5 w-5 text-accent-400" />
      </div>
      <div className="flex items-baseline gap-2">
        <span className="text-2xl font-bold tracking-tight text-surface-50">{metric.value}</span>
        {hasChange && (
          <span
            className={cn(
              'text-sm font-medium',
              metric.change! > 0 ? 'text-success' : metric.change! < 0 ? 'text-error' : 'text-surface-400',
            )}
          >
            {metric.change! > 0 ? '+' : ''}
            {metric.change}
          </span>
        )}
      </div>
      {metric.changeLabel && <span className="text-xs text-surface-500">{metric.changeLabel}</span>}
    </button>
  );
}
