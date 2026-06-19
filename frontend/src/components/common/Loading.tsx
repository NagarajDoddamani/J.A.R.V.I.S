import { cn } from '@/utils';

interface LoadingProps {
  size?: 'sm' | 'md' | 'lg';
  label?: string;
  fullPage?: boolean;
}

export function Loading({ size = 'md', label, fullPage = false }: LoadingProps) {
  const sizeMap = { sm: 'h-5 w-5', md: 'h-8 w-8', lg: 'h-12 w-12' };
  const borderMap = { sm: 'border-2', md: 'border-[3px]', lg: 'border-4' };

  const spinner = (
    <div role="status" className="flex flex-col items-center justify-center gap-3" aria-label={label ?? 'Loading'}>
      <div
        className={cn(
          'animate-spin rounded-full border-accent-600 border-t-transparent',
          sizeMap[size],
          borderMap[size],
        )}
      />
      {label && <p className="text-sm text-surface-400">{label}</p>}
      <span className="sr-only">{label ?? 'Loading...'}</span>
    </div>
  );

  if (fullPage) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        {spinner}
      </div>
    );
  }

  return spinner;
}
