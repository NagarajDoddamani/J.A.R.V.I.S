import { useState } from 'react';
import { Save } from 'lucide-react';

import { cn } from '@/utils';
import type { SettingSection } from '@/types';

const MOCK_SETTINGS: SettingSection[] = [
  {
    id: 'general',
    title: 'General',
    description: 'Core application settings',
    icon: 'Settings',
    fields: [
      { key: 'app_name', label: 'Application Name', type: 'text', value: 'J.A.R.V.I.S AI Brain', description: 'The display name for this instance' },
      { key: 'language', label: 'Language', type: 'select', value: 'en', options: [{ label: 'English', value: 'en' }, { label: 'Spanish', value: 'es' }] },
      { key: 'log_level', label: 'Log Level', type: 'select', value: 'info', options: [{ label: 'Debug', value: 'debug' }, { label: 'Info', value: 'info' }, { label: 'Warn', value: 'warn' }, { label: 'Error', value: 'error' }] },
    ],
  },
  {
    id: 'ai',
    title: 'AI Configuration',
    description: 'Model and inference settings',
    icon: 'Brain',
    fields: [
      { key: 'model', label: 'Default Model', type: 'select', value: 'llama3.1:8b', options: [{ label: 'Llama 3.1 8B', value: 'llama3.1:8b' }, { label: 'Llama 3.1 70B', value: 'llama3.1:70b' }, { label: 'Mistral 7B', value: 'mistral:7b' }] },
      { key: 'temperature', label: 'Temperature', type: 'number', value: 0.7, description: 'Controls randomness (0-2)' },
      { key: 'max_tokens', label: 'Max Tokens', type: 'number', value: 2048, description: 'Maximum response length' },
    ],
  },
  {
    id: 'memory',
    title: 'Memory Settings',
    description: 'Memory and vector store configuration',
    icon: 'Database',
    fields: [
      { key: 'retention_days', label: 'Memory Retention (days)', type: 'number', value: 90, description: 'Days before memories are archived' },
      { key: 'auto_summarize', label: 'Auto-summarize', type: 'boolean', value: true, description: 'Automatically summarize old memories' },
    ],
  },
];

export function SettingsPage() {
  const [values, setValues] = useState<Record<string, string | number | boolean>>(() => {
    const initial: Record<string, string | number | boolean> = {};
    for (const section of MOCK_SETTINGS) {
      for (const field of section.fields) {
        initial[field.key] = field.value;
      }
    }
    return initial;
  });

  function updateValue(key: string, val: string | number | boolean) {
    setValues((prev) => ({ ...prev, [key]: val }));
  }

  return (
    <div className="max-w-3xl space-y-6">
      {MOCK_SETTINGS.map((section) => (
        <div key={section.id} className="rounded-xl border border-surface-800 bg-surface-900 p-6">
          <div className="mb-5">
            <h3 className="text-lg font-semibold text-surface-100">{section.title}</h3>
            <p className="text-sm text-surface-400">{section.description}</p>
          </div>

          <div className="space-y-4">
            {section.fields.map((field) => (
              <div key={field.key}>
                <label className="block text-sm font-medium text-surface-200">{field.label}</label>
                {field.description && (
                  <p className="mb-2 text-xs text-surface-500">{field.description}</p>
                )}
                {field.type === 'boolean' ? (
                  <button
                    type="button"
                    onClick={() => updateValue(field.key, !values[field.key])}
                    className={cn(
                      'relative mt-1 inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors',
                      values[field.key] ? 'bg-accent-600' : 'bg-surface-700',
                    )}
                  >
                    <span
                      className={cn(
                        'inline-block h-5 w-5 rounded-full bg-white shadow transition-transform',
                        values[field.key] ? 'translate-x-5' : 'translate-x-0',
                      )}
                    />
                  </button>
                ) : field.type === 'select' ? (
                  <select
                    value={String(values[field.key])}
                    onChange={(e) => updateValue(field.key, e.target.value)}
                    className="mt-1 w-full rounded-lg border border-surface-700 bg-surface-800 px-3 py-2 text-sm text-surface-200 focus:border-accent-500 focus:outline-none focus:ring-1 focus:ring-accent-500"
                  >
                    {field.options?.map((opt) => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </select>
                ) : (
                  <input
                    type={field.type}
                    value={String(values[field.key])}
                    onChange={(e) => updateValue(field.key, field.type === 'number' ? Number(e.target.value) : e.target.value)}
                    className="mt-1 w-full rounded-lg border border-surface-700 bg-surface-800 px-3 py-2 text-sm text-surface-200 focus:border-accent-500 focus:outline-none focus:ring-1 focus:ring-accent-500"
                  />
                )}
              </div>
            ))}
          </div>
        </div>
      ))}

      <div className="flex justify-end">
        <button
          type="button"
          className="flex items-center gap-2 rounded-xl bg-accent-600 px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-accent-500"
        >
          <Save className="h-4 w-4" />
          Save Changes
        </button>
      </div>
    </div>
  );
}
