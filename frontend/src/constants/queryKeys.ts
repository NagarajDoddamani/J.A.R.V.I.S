export const queryKeys = {
  health: {
    all: ['health'] as const,
    status: () => [...queryKeys.health.all, 'status'] as const,
  },
  memory: {
    all: ['memory'] as const,
    list: (params?: Record<string, string>) => [...queryKeys.memory.all, 'list', params] as const,
    detail: (id: string) => [...queryKeys.memory.all, 'detail', id] as const,
  },
  knowledge: {
    all: ['knowledge'] as const,
    list: () => [...queryKeys.knowledge.all, 'list'] as const,
  },
  research: {
    all: ['research'] as const,
    list: () => [...queryKeys.research.all, 'list'] as const,
  },
  agents: {
    all: ['agents'] as const,
    list: () => [...queryKeys.agents.all, 'list'] as const,
  },
};
