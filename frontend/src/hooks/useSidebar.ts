import { useState, useCallback } from 'react';

import { STORAGE_KEYS } from '@/constants';

export function useSidebar() {
  const [collapsed, setCollapsed] = useState(() => {
    const stored = localStorage.getItem(STORAGE_KEYS.SIDEBAR);
    return stored === 'true';
  });

  const toggle = useCallback(() => {
    setCollapsed((prev) => {
      localStorage.setItem(STORAGE_KEYS.SIDEBAR, String(!prev));
      return !prev;
    });
  }, []);

  return { collapsed, toggle };
}
