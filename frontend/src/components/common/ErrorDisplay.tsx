import { AlertCircle, RefreshCw } from 'lucide-react';

interface ErrorDisplayProps {
  message: string;
  onRetry?: () => void;
}

export function ErrorDisplay({ message, onRetry }: ErrorDisplayProps) {
  return (
    <div
      role="alert"
      className="flex flex-col items-center justify-center gap-5 rounded-xl border border-error/20 bg-error/5 px-6 py-14"
    >
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-error/10">
        <AlertCircle className="h-6 w-6 text-error" />
      </div>
      <p className="text-center text-sm text-surface-300">{message}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="flex items-center gap-2 rounded-lg bg-accent-600 px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-accent-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-400"
        >
          <RefreshCw className="h-4 w-4" />
          Retry
        </button>
      )}
    </div>
  );
}
