import type { ServiceStatus, MetricData, MemoryItem, KnowledgeSource, ResearchRequest, Agent, ChatMessage, ChatSession } from '@/types';

export const MOCK_SERVICES: ServiceStatus[] = [
  { name: 'PostgreSQL', status: 'healthy', latency: 2, lastChecked: new Date().toISOString() },
  { name: 'Redis', status: 'healthy', latency: 1, lastChecked: new Date().toISOString() },
  { name: 'NATS', status: 'healthy', latency: 3, lastChecked: new Date().toISOString() },
  { name: 'Qdrant', status: 'healthy', latency: 4, lastChecked: new Date().toISOString() },
  { name: 'Ollama', status: 'healthy', latency: 45, lastChecked: new Date().toISOString() },
];

export const MOCK_METRICS: MetricData[] = [
  { label: 'Active Memories', value: 1284, change: 12, changeLabel: 'vs last hour', icon: 'Brain' },
  { label: 'Knowledge Sources', value: 47, change: 3, changeLabel: 'vs yesterday', icon: 'BookOpen' },
  { label: 'Research Queries', value: 892, change: -5, changeLabel: 'vs yesterday', icon: 'Search' },
  { label: 'Active Agents', value: 6, icon: 'Bot' },
  { label: 'Avg Response Time', value: '142ms', change: -8, changeLabel: 'vs last hour', icon: 'Gauge' },
  { label: 'Memory Usage', value: '3.2 GB', change: 5, changeLabel: 'of 16 GB', icon: 'HardDrive' },
];

export const MOCK_MEMORIES: MemoryItem[] = [
  { id: 'mem-001', content: 'User prefers dark mode for all interfaces', category: 'preference', timestamp: new Date(Date.now() - 3600000).toISOString(), source: 'conversation' },
  { id: 'mem-002', content: 'Project deadline is end of Q3 2026', category: 'fact', timestamp: new Date(Date.now() - 7200000).toISOString(), source: 'conversation' },
  { id: 'mem-003', content: 'Integration with external API requires OAuth2', category: 'insight', timestamp: new Date(Date.now() - 14400000).toISOString(), source: 'inference' },
  { id: 'mem-004', content: 'Favorite programming language is Python', category: 'preference', timestamp: new Date(Date.now() - 28800000).toISOString(), source: 'conversation' },
  { id: 'mem-005', content: 'Recently read article about vector databases', category: 'document', timestamp: new Date(Date.now() - 86400000).toISOString(), source: 'system' },
];

export const MOCK_KNOWLEDGE_SOURCES: KnowledgeSource[] = [
  { id: 'src-001', name: 'Technical Documentation', type: 'file', status: 'active', documentCount: 156, lastIngested: new Date(Date.now() - 3600000).toISOString() },
  { id: 'src-002', name: 'Research Papers', type: 'file', status: 'active', documentCount: 89, lastIngested: new Date(Date.now() - 7200000).toISOString() },
  { id: 'src-003', name: 'API Reference', type: 'url', status: 'active', documentCount: 34, lastIngested: new Date(Date.now() - 14400000).toISOString() },
  { id: 'src-004', name: 'Meeting Notes', type: 'file', status: 'inactive', documentCount: 23, lastIngested: new Date(Date.now() - 604800000).toISOString() },
  { id: 'src-005', name: 'Code Repositories', type: 'url', status: 'active', documentCount: 212, lastIngested: new Date(Date.now() - 1800000).toISOString() },
];

export const MOCK_RESEARCH_REQUESTS: ResearchRequest[] = [
  { id: 'req-001', query: 'Latest advances in LLM quantization', status: 'completed', priority: 'high', createdAt: new Date(Date.now() - 3600000).toISOString(), agentId: 'agent-001' },
  { id: 'req-002', query: 'Comparison of vector database performance', status: 'in_progress', priority: 'medium', createdAt: new Date(Date.now() - 7200000).toISOString(), agentId: 'agent-002' },
  { id: 'req-003', query: 'RAG architecture best practices 2026', status: 'completed', priority: 'high', createdAt: new Date(Date.now() - 14400000).toISOString(), agentId: 'agent-001' },
  { id: 'req-004', query: 'MCP protocol specification analysis', status: 'pending', priority: 'low', createdAt: new Date(Date.now() - 28800000).toISOString(), agentId: 'agent-003' },
  { id: 'req-005', query: 'Agent orchestration patterns', status: 'failed', priority: 'medium', createdAt: new Date(Date.now() - 86400000).toISOString(), agentId: 'agent-002' },
];

export const MOCK_AGENTS: Agent[] = [
  { id: 'agent-001', name: 'Research Agent', status: 'active', type: 'research', lastActive: new Date(Date.now() - 60000).toISOString(), taskCount: 23 },
  { id: 'agent-002', name: 'Memory Agent', status: 'active', type: 'memory', lastActive: new Date(Date.now() - 120000).toISOString(), taskCount: 45 },
  { id: 'agent-003', name: 'Planner Agent', status: 'idle', type: 'planner', lastActive: new Date(Date.now() - 300000).toISOString(), taskCount: 12 },
  { id: 'agent-004', name: 'Knowledge Agent', status: 'active', type: 'knowledge', lastActive: new Date(Date.now() - 180000).toISOString(), taskCount: 31 },
  { id: 'agent-005', name: 'Policy Agent', status: 'idle', type: 'policy', lastActive: new Date(Date.now() - 600000).toISOString(), taskCount: 8 },
  { id: 'agent-006', name: 'Orchestrator Agent', status: 'active', type: 'orchestrator', lastActive: new Date(Date.now() - 90000).toISOString(), taskCount: 56 },
];

export function createMockChatSession(title: string): ChatSession {
  return {
    id: crypto.randomUUID(),
    title,
    messages: [
      {
        id: crypto.randomUUID(),
        role: 'system',
        content: 'Session started. J.A.R.V.I.S AI Brain is ready.',
        timestamp: new Date().toISOString(),
      },
    ],
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  };
}

export const MOCK_MESSAGES: ChatMessage[] = [
  {
    id: 'msg-001',
    role: 'user',
    content: 'What are the latest research findings on RAG architectures?',
    timestamp: new Date(Date.now() - 300000).toISOString(),
  },
  {
    id: 'msg-002',
    role: 'assistant',
    content: "Based on my analysis of recent papers, here are the key findings:\n\n1. **Hybrid retrieval** combining sparse and dense vectors improves recall by 15-20%\n2. **Agentic RAG** patterns are emerging where LLMs dynamically choose retrieval strategies\n3. **Latency optimization** through KV-cache sharing shows promise for real-time applications\n\nWould you like me to dive deeper into any of these areas?",
    timestamp: new Date(Date.now() - 295000).toISOString(),
  },
  {
    id: 'msg-003',
    role: 'user',
    content: 'Yes, tell me more about agentic RAG patterns.',
    timestamp: new Date(Date.now() - 240000).toISOString(),
  },
  {
    id: 'msg-004',
    role: 'assistant',
    content: "Agentic RAG represents a paradigm shift where the LLM acts as an **orchestrator** rather than just a reader.\n\n### Key Patterns:\n\n- **Self-RAG**: The model decides when to retrieve, what to retrieve, and how to use results\n- **CRAG**: Corrective RAG — validates retrieved documents before generation\n- **Adaptive RAG**: Dynamically routes queries to different retrieval strategies\n\n```python\n# Conceptual example\nif query_complexity == 'simple':\n    result = direct_generate(query)\nelif query_complexity == 'medium':\n    result = retrieve_and_generate(query)\nelse:\n    result = multi_step_research(query)\n```\n\nWould you like me to set up a research request to explore this further?",
    timestamp: new Date(Date.now() - 235000).toISOString(),
  },
];

export const MOCK_CHAT_SESSIONS: ChatSession[] = [
  {
    id: 'session-001',
    title: 'RAG Architecture Research',
    messages: MOCK_MESSAGES,
    createdAt: new Date(Date.now() - 3600000).toISOString(),
    updatedAt: new Date(Date.now() - 235000).toISOString(),
  },
  {
    id: 'session-002',
    title: 'Code Review: Vector Search',
    messages: [MOCK_MESSAGES[0], MOCK_MESSAGES[1]],
    createdAt: new Date(Date.now() - 86400000).toISOString(),
    updatedAt: new Date(Date.now() - 82800000).toISOString(),
  },
  {
    id: 'session-003',
    title: 'System Architecture Discussion',
    messages: [MOCK_MESSAGES[0]],
    createdAt: new Date(Date.now() - 172800000).toISOString(),
    updatedAt: new Date(Date.now() - 165600000).toISOString(),
  },
];
