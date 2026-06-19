import { type ReactNode } from 'react';
import { Navigate } from 'react-router-dom';

import { ROUTES } from '@/constants';

interface ProtectedRouteProps {
  children: ReactNode;
  requiredPermission?: string;
}

export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const isAuthenticated = true;

  if (!isAuthenticated) {
    return <Navigate to={ROUTES.DASHBOARD} replace />;
  }

  return <>{children}</>;
}
