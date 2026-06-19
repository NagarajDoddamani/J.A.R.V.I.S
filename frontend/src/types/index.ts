export type ThemeMode = 'dark' | 'light';

export interface NavigationItem {
  label: string;
  path: string;
  icon: string;
  badge?: number;
}

export interface ServiceStatus {
  name: string;
  status: 'healthy' | 'degraded' | 'down' | 'unknown';
  latency: number;
  lastChecked: string;
}

export interface MetricData {
  label: string;
  value: string | number;
  change?: number;
  changeLabel?: string;
  icon: string;
}

export interface MemoryItem {
  id: string;
  content: string;
  category: string;
  timestamp: string;
  source: string;
}

export interface KnowledgeSource {
  id: string;
  name: string;
  type: string;
  status: string;
  documentCount: number;
  lastIngested: string;
}

export interface ResearchRequest {
  id: string;
  query: string;
  status: string;
  priority: string;
  createdAt: string;
  agentId: string;
}

export interface Agent {
  id: string;
  name: string;
  status: string;
  type: string;
  lastActive: string;
  taskCount: number;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
}

export interface ChatSession {
  id: string;
  title: string;
  messages: ChatMessage[];
  createdAt: string;
  updatedAt: string;
}

export interface SettingSection {
  id: string;
  title: string;
  description: string;
  icon: string;
  fields: SettingField[];
}

export interface SettingField {
  key: string;
  label: string;
  type: 'text' | 'number' | 'boolean' | 'select' | 'password';
  value: string | number | boolean;
  options?: { label: string; value: string }[];
  description?: string;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  pageSize: number;
}

export interface ApiError {
  message: string;
  code: string;
  status: number;
}

export type StatusVariant = 'healthy' | 'degraded' | 'down' | 'unknown' | 'active' | 'inactive' | 'pending' | 'error';
