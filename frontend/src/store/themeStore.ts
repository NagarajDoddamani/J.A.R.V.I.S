import { create } from 'zustand';
import { persist } from 'zustand/middleware';

import type { ThemeMode } from '@/types';

interface ThemeState {
  theme: ThemeMode;
  toggle: () => void;
  setTheme: (mode: ThemeMode) => void;
}

export const useThemeStore = create<ThemeState>()(
  persist(
    (set) => ({
      theme: 'dark',
      toggle: () => set((state) => ({ theme: state.theme === 'dark' ? 'light' : 'dark' })),
      setTheme: (mode) => set({ theme: mode }),
    }),
    { name: 'jarvis-theme' },
  ),
);
