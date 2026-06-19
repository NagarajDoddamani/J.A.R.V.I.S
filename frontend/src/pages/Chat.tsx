import { useState } from 'react';
import { Send, Plus, MessageSquare } from 'lucide-react';

import { cn, formatTimestamp } from '@/utils';
import { MOCK_CHAT_SESSIONS } from '@/services/mockData';
import type { ChatSession, ChatMessage } from '@/types';

export function ChatPage() {
  const [sessions] = useState<ChatSession[]>(MOCK_CHAT_SESSIONS);
  const [activeSessionId, setActiveSessionId] = useState<string>(sessions[0]?.id ?? '');
  const [input, setInput] = useState('');

  const activeSession = sessions.find((s) => s.id === activeSessionId);
  const messages: ChatMessage[] = activeSession?.messages ?? [];

  function handleSend() {
    if (!input.trim()) return;
    setInput('');
  }

  return (
    <div className="flex h-[calc(100vh-8rem)] gap-4">
      <div className="hidden w-64 shrink-0 flex-col rounded-xl border border-surface-800 bg-surface-900 md:flex">
        <div className="border-b border-surface-800 p-3">
          <button
            type="button"
            className="flex w-full items-center gap-2 rounded-lg border border-dashed border-surface-700 px-3 py-2 text-sm text-surface-400 transition-colors hover:border-accent-600 hover:text-accent-400"
          >
            <Plus className="h-4 w-4" />
            New Chat
          </button>
        </div>
        <div className="flex-1 space-y-1 overflow-y-auto p-2">
          {sessions.map((session) => (
            <button
              key={session.id}
              type="button"
              onClick={() => setActiveSessionId(session.id)}
              className={cn(
                'flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm transition-colors',
                session.id === activeSessionId
                  ? 'bg-accent-600/15 text-accent-400'
                  : 'text-surface-400 hover:bg-surface-800 hover:text-surface-200',
              )}
            >
              <MessageSquare className="h-4 w-4 shrink-0" />
              <span className="truncate">{session.title}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="flex flex-1 flex-col rounded-xl border border-surface-800 bg-surface-900">
        <div className="flex-1 space-y-4 overflow-y-auto p-4">
          {messages.length === 0 && (
            <div className="flex h-full items-center justify-center">
              <p className="text-sm text-surface-500">Start a conversation with J.A.R.V.I.S</p>
            </div>
          )}
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={cn(
                'flex gap-3',
                msg.role === 'user' ? 'justify-end' : 'justify-start',
              )}
            >
              {msg.role !== 'user' && (
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-accent-600/20 text-xs font-bold text-accent-400">
                  J
                </div>
              )}
              <div
                className={cn(
                  'max-w-[75%] rounded-2xl px-4 py-3',
                  msg.role === 'user'
                    ? 'bg-accent-600 text-white'
                    : msg.role === 'system'
                      ? 'bg-surface-800 text-surface-400 text-sm italic'
                      : 'bg-surface-800 text-surface-200',
                )}
              >
                <p className="whitespace-pre-wrap text-sm leading-relaxed">{msg.content}</p>
                <p className="mt-1 text-right text-xs text-surface-500">
                  {formatTimestamp(msg.timestamp)}
                </p>
              </div>
              {msg.role === 'user' && (
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-accent-600 text-xs font-bold text-white">
                  U
                </div>
              )}
            </div>
          ))}
        </div>

        <div className="border-t border-surface-800 p-4">
          <div className="flex gap-3">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              placeholder="Type your message..."
              className={cn(
                'flex-1 rounded-xl border border-surface-700 bg-surface-800 px-4 py-3 text-sm text-surface-200',
                'placeholder:text-surface-500',
                'focus:border-accent-500 focus:outline-none focus:ring-1 focus:ring-accent-500',
              )}
            />
            <button
              type="button"
              onClick={handleSend}
              className="flex items-center justify-center rounded-xl bg-accent-600 px-4 text-white transition-colors hover:bg-accent-500"
            >
              <Send className="h-5 w-5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
