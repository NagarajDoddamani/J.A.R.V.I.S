import { NavLink } from 'react-router-dom';
import * as IconSet from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { ChevronLeft, ChevronRight } from 'lucide-react';

import { NAV_ITEMS } from '@/constants';
import { cn } from '@/utils';

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

export function Sidebar({ collapsed, onToggle }: SidebarProps) {
  return (
    <aside
      className={cn(
        'flex flex-col border-r border-surface-800 bg-surface-900 transition-all duration-300 ease-in-out',
        collapsed ? 'w-16' : 'w-60',
      )}
    >
      <div className={cn('flex items-center border-b border-surface-800 px-4 py-5', collapsed && 'justify-center')}>
        {!collapsed && (
          <span className="text-lg font-bold tracking-tight text-surface-50">
            J.A.R.V.I.S
          </span>
        )}
        {collapsed && (
          <span className="text-lg font-bold text-accent-400">J</span>
        )}
      </div>

      <nav className="flex-1 space-y-1 px-2 py-4">
        {NAV_ITEMS.map((item) => {
          const IconComponent = (IconSet as unknown as Record<string, LucideIcon>)[item.icon] ?? IconSet.Box;
          return (
            <NavLink
              key={item.path}
              to={item.path}
              aria-label={item.label}
              className={({ isActive }: { isActive: boolean }) =>
                cn(
                  'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors duration-150',
                  isActive
                    ? 'bg-accent-600/15 text-accent-400'
                    : 'text-surface-400 hover:bg-surface-800 hover:text-surface-200',
                  collapsed && 'justify-center px-2',
                )
              }
            >
              <IconComponent className="h-5 w-5 shrink-0" />
              {!collapsed && <span>{item.label}</span>}
            </NavLink>
          );
        })}
      </nav>

      <div className="border-t border-surface-800 p-2">
        <button
          type="button"
          onClick={onToggle}
          className="flex w-full items-center justify-center gap-2 rounded-lg px-3 py-2.5 text-sm text-surface-400 transition-colors hover:bg-surface-800 hover:text-surface-200"
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
          {!collapsed && <span>Collapse</span>}
        </button>
      </div>
    </aside>
  );
}
