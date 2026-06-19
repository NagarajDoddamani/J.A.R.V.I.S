import { createBrowserRouter, Navigate } from 'react-router-dom';

import { MainLayout } from '@/layouts/MainLayout';
import { ProtectedRoute } from '@/routes/ProtectedRoute';
import { DashboardPage } from '@/pages/Dashboard';
import { ChatPage } from '@/pages/Chat';
import { MemoryPage } from '@/pages/Memory';
import { KnowledgePage } from '@/pages/Knowledge';
import { ResearchPage } from '@/pages/Research';
import { AgentsPage } from '@/pages/Agents';
import { SettingsPage } from '@/pages/Settings';
import { NotFoundPage } from '@/pages/NotFound';
import { ROUTES } from '@/constants';

export const router = createBrowserRouter([
  {
    path: '/',
    element: (
      <ProtectedRoute>
        <MainLayout />
      </ProtectedRoute>
    ),
    children: [
      { index: true, element: <DashboardPage /> },
      { path: ROUTES.CHAT, element: <ChatPage /> },
      { path: ROUTES.MEMORY, element: <MemoryPage /> },
      { path: ROUTES.KNOWLEDGE, element: <KnowledgePage /> },
      { path: ROUTES.RESEARCH, element: <ResearchPage /> },
      { path: ROUTES.AGENTS, element: <AgentsPage /> },
      { path: ROUTES.SETTINGS, element: <SettingsPage /> },
    ],
  },
  {
    path: '/404',
    element: <NotFoundPage />,
  },
  {
    path: '*',
    element: <Navigate to="/404" replace />,
  },
]);
