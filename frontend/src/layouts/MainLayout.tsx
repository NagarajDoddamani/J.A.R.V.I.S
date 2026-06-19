import { Outlet } from 'react-router-dom';

import { Sidebar } from '@/components/layout/Sidebar';
import { TopNav } from '@/components/layout/TopNav';
import { useUiStore } from '@/store';
import { cn } from '@/utils';

const PAGE_TITLES: Record<string, string> = {
  '/': 'Dashboard',
  '/chat': 'Chat',
  '/memory': 'Memory',
  '/knowledge': 'Knowledge',
  '/research': 'Research',
  '/agents': 'Agents',
  '/settings': 'Settings',
};

export function MainLayout() {
  const collapsed = useUiStore((s) => s.sidebarCollapsed);
  const toggle = useUiStore((s) => s.toggleSidebar);

  const path = window.location.pathname;
  const title = PAGE_TITLES[path] ?? 'J.A.R.V.I.S';

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar collapsed={collapsed} onToggle={toggle} />
      <div className={cn('flex flex-1 flex-col overflow-hidden transition-all duration-300')}>
        <TopNav title={title} />
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
