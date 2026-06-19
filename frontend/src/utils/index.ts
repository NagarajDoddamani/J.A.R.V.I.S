export function cn(...classes: (string | false | null | undefined)[]): string {
  return classes.filter(Boolean).join(' ');
}

export function formatTimestamp(iso: string): string {
  const date = new Date(iso);
  return date.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function truncate(str: string, length: number): string {
  if (str.length <= length) return str;
  return str.slice(0, length) + '...';
}

export function statusColor(status: string): string {
  const map: Record<string, string> = {
    healthy: 'text-success',
    degraded: 'text-warning',
    down: 'text-error',
    active: 'text-success',
    inactive: 'text-surface-400',
    pending: 'text-warning',
    error: 'text-error',
    unknown: 'text-surface-400',
  };
  return map[status] ?? 'text-surface-400';
}

export function statusBgColor(status: string): string {
  const map: Record<string, string> = {
    healthy: 'bg-success/10',
    degraded: 'bg-warning/10',
    down: 'bg-error/10',
    active: 'bg-success/10',
    inactive: 'bg-surface-800',
    pending: 'bg-warning/10',
    error: 'bg-error/10',
    unknown: 'bg-surface-800',
  };
  return map[status] ?? 'bg-surface-800';
}
