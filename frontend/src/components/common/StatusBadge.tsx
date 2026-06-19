import type { StatusVariant } from '@/types';
import { cn, statusColor, statusBgColor } from '@/utils';

interface StatusBadgeProps {
  status: StatusVariant;
  label?: string;
  size?: 'sm' | 'md';
}

const LABEL_MAP: Record<string, string> = {
  healthy: 'Healthy',
  degraded: 'Degraded',
  down: 'Down',
  active: 'Active',
  inactive: 'Inactive',
  pending: 'Pending',
  error: 'Error',
  unknown: 'Unknown',
};

export function StatusBadge({ status, label, size = 'md' }: StatusBadgeProps) {
  const text = label ?? LABEL_MAP[status] ?? status;
  const dotColor = statusColor(status);
  const bgColor = statusBgColor(status);
  const isSmall = size === 'sm';

  return (
    <span
      role="status"
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full font-medium',
        bgColor,
        isSmall ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-sm',
      )}
      aria-label={`Status: ${text}`}
    >
      <span className={cn('inline-block rounded-full', dotColor, isSmall ? 'h-1.5 w-1.5' : 'h-2 w-2', 'bg-current')} />
      {text}
    </span>
  );
}
