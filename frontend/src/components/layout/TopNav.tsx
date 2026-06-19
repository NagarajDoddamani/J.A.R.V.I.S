import { Bell, Moon, Sun, Search } from 'lucide-react';

import { useThemeStore } from '@/store';
import { cn } from '@/utils';

interface TopNavProps {
  title: string;
}

export function TopNav({ title }: TopNavProps) {
  const theme = useThemeStore((s) => s.theme);
  const toggle = useThemeStore((s) => s.toggle);

  return (
    <header className="flex h-16 items-center justify-between border-b border-surface-800 bg-surface-900/80 px-6 backdrop-blur-sm">
      <h1 className="text-lg font-semibold text-surface-50">{title}</h1>

      <div className="flex items-center gap-3">
        <div className="relative hidden md:block">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-surface-400" />
          <input
            type="text"
            placeholder="Search..."
            aria-label="Search"
            className={cn(
              'w-64 rounded-lg border border-surface-700 bg-surface-800 py-2 pl-10 pr-4 text-sm text-surface-200',
              'placeholder:text-surface-500',
              'focus:border-accent-500 focus:outline-none focus:ring-1 focus:ring-accent-500',
            )}
          />
        </div>

        <button
          type="button"
          onClick={toggle}
          className="rounded-lg p-2 text-surface-400 transition-colors hover:bg-surface-800 hover:text-surface-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-500"
          aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
          aria-pressed={theme === 'light'}
        >
          {theme === 'dark' ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
        </button>

        <button
          type="button"
          className="relative rounded-lg p-2 text-surface-400 transition-colors hover:bg-surface-800 hover:text-surface-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-500"
          aria-label="Notifications"
        >
          <Bell className="h-5 w-5" />
          <span className="absolute right-1.5 top-1.5 h-2 w-2 rounded-full bg-accent-500" />
        </button>

        <div
          className="ml-2 flex h-8 w-8 items-center justify-center rounded-full bg-accent-600 text-sm font-medium text-white"
          aria-label="User avatar"
          role="img"
        >
          J
        </div>
      </div>
    </header>
  );
}
