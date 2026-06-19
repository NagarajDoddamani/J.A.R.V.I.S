import { apiClient } from './client';

import type { MemoryItem, KnowledgeSource, ResearchRequest, Agent, ChatSession, PaginatedResponse } from '@/types';

export async function fetchHealth(): Promise<{ status: string; services: Record<string, string> }> {
  const { data } = await apiClient.get('/health');
  return data;
}

export async function fetchMemoryList(params?: { page?: number; pageSize?: number }): Promise<PaginatedResponse<MemoryItem>> {
  const { data } = await apiClient.get('/memory/memories', { params });
  return data;
}

export async function fetchKnowledgeSources(params?: { page?: number; pageSize?: number }): Promise<PaginatedResponse<KnowledgeSource>> {
  const { data } = await apiClient.get('/knowledge/sources', { params });
  return data;
}

export async function fetchResearchRequests(params?: { page?: number; pageSize?: number }): Promise<PaginatedResponse<ResearchRequest>> {
  const { data } = await apiClient.get('/research/requests', { params });
  return data;
}

export async function fetchAgents(params?: { page?: number; pageSize?: number }): Promise<PaginatedResponse<Agent>> {
  const { data } = await apiClient.get('/agent/', { params });
  return data;
}

export async function fetchChatSessions(): Promise<ChatSession[]> {
  const { data } = await apiClient.get('/chat/sessions');
  return data;
}

export async function sendMessage(sessionId: string, content: string): Promise<ChatSession> {
  const { data } = await apiClient.post(`/chat/sessions/${sessionId}/messages`, { content });
  return data;
}
