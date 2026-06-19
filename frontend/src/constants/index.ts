export const ROUTES = {
  DASHBOARD: '/',
  CHAT: '/chat',
  MEMORY: '/memory',
  KNOWLEDGE: '/knowledge',
  RESEARCH: '/research',
  AGENTS: '/agents',
  SETTINGS: '/settings',
} as const;

import type { NavigationItem } from '@/types';

export const NAV_ITEMS: NavigationItem[] = [
  { label: 'Dashboard', path: ROUTES.DASHBOARD, icon: 'LayoutDashboard' },
  { label: 'Chat', path: ROUTES.CHAT, icon: 'MessageSquare' },
  { label: 'Memory', path: ROUTES.MEMORY, icon: 'Brain' },
  { label: 'Knowledge', path: ROUTES.KNOWLEDGE, icon: 'BookOpen' },
  { label: 'Research', path: ROUTES.RESEARCH, icon: 'Search' },
  { label: 'Agents', path: ROUTES.AGENTS, icon: 'Bot' },
  { label: 'Settings', path: ROUTES.SETTINGS, icon: 'Settings' },
];

export const API_BASE_URL = '/api/v1';

export const STORAGE_KEYS = {
  THEME: 'jarvis-theme',
  SIDEBAR: 'jarvis-sidebar',
} as const;

export const POLL_INTERVALS = {
  STATUS: 10000,
  MEMORY: 15000,
  NOTIFICATIONS: 30000,
} as const;
