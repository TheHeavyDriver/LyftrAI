import { useState, type ChangeEvent } from 'react';

interface SystemPromptPanelProps {
  onSystemPromptChange: (prompt: string) => void;
  disabled?: boolean;
}

const MAX_LENGTH = 4000;

export function SystemPromptPanel({
  onSystemPromptChange,
  disabled = false,
}: SystemPromptPanelProps) {
  const [expanded, setExpanded] = useState(false);
  const [value, setValue] = useState('');

  const handleChange = (e: ChangeEvent<HTMLTextAreaElement>) => {
    const newValue = e.target.value;
    setValue(newValue);
    onSystemPromptChange(newValue);
  };

  const handleReset = () => {
    setValue('');
    onSystemPromptChange('');
  };

  return (
    <div className="border-t border-border-subtle bg-warm-surface px-4 py-3">
      <div className="mx-auto max-w-4xl">
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex w-full items-center justify-between text-sm font-medium text-ink hover:text-signal-green focus:outline-none focus:ring-2 focus:ring-signal-green"
          aria-expanded={expanded}
        >
          <span>System Prompt (Optional)</span>
          <span className="text-ink-muted">{expanded ? '▲' : '▼'}</span>
        </button>

        {expanded && (
          <div className="mt-3 space-y-2">
            <textarea
              data-testid="system-prompt-input"
              value={value}
              onChange={handleChange}
              disabled={disabled}
              maxLength={MAX_LENGTH}
              placeholder="Custom system instructions for this session..."
              className="w-full resize-none rounded-lg border border-border-subtle bg-white px-3 py-2 text-sm text-ink placeholder-ink-muted focus:outline-none focus:ring-2 focus:ring-signal-green disabled:bg-warm-surface disabled:text-ink-muted"
              rows={3}
            />
            <div className="flex items-center justify-between">
              <p className="text-xs text-ink-muted">
                Applies to all messages in this session. Clear to use default.
              </p>
              <button
                onClick={handleReset}
                disabled={disabled || !value}
                className="text-xs text-signal-green hover:underline disabled:text-ink-muted focus:outline-none focus:ring-2 focus:ring-signal-green"
              >
                Reset
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
