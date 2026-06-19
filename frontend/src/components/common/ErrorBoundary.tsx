import { ErrorBoundary as ReactErrorBoundary, type FallbackProps } from 'react-error-boundary';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import type { ReactNode } from 'react';

function ErrorFallback({ error, resetErrorBoundary }: FallbackProps) {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-5 px-6">
      <div className="flex h-14 w-14 items-center justify-center rounded-full bg-error/10">
        <AlertTriangle className="h-7 w-7 text-error" />
      </div>
      <div className="text-center">
        <h2 className="text-lg font-semibold text-surface-100">Something went wrong</h2>
        <p className="mt-1 text-sm text-surface-400">
          {import.meta.env.DEV && error instanceof Error ? error.message : 'An unexpected error occurred. Please try again.'}
        </p>
      </div>
      <button
        type="button"
        onClick={resetErrorBoundary}
        className="flex items-center gap-2 rounded-lg bg-accent-600 px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-accent-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-400"
      >
        <RefreshCw className="h-4 w-4" />
        Try again
      </button>
    </div>
  );
}

interface ErrorBoundaryProps {
  children: ReactNode;
}

export function ErrorBoundary({ children }: ErrorBoundaryProps) {
  return (
    <ReactErrorBoundary FallbackComponent={ErrorFallback}>
      {children}
    </ReactErrorBoundary>
  );
}
