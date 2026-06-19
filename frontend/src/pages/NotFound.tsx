import { Link } from 'react-router-dom';
import { Home } from 'lucide-react';

import { ROUTES } from '@/constants';

export function NotFoundPage() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-6">
      <div className="text-6xl font-bold text-surface-600">404</div>
      <h2 className="text-xl font-semibold text-surface-200">Page Not Found</h2>
      <p className="text-sm text-surface-400">The page you are looking for does not exist.</p>
      <Link
        to={ROUTES.DASHBOARD}
        className="flex items-center gap-2 rounded-lg bg-accent-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-accent-500"
      >
        <Home className="h-4 w-4" />
        Back to Dashboard
      </Link>
    </div>
  );
}
