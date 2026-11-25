import { useRef, useEffect, useState, type ChangeEvent, type KeyboardEvent } from 'react';

interface ChatComposerProps {
  onSend: (message: string) => void;
  disabled?: boolean;
}

const MAX_LENGTH = 4000;

export function ChatComposer({ onSend, disabled = false }: ChatComposerProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [length, setLength] = useState(0);

  const handleSend = () => {
    const message = textareaRef.current?.value.trim();
    if (message) {
      onSend(message);
      setLength(0);
      if (textareaRef.current) {
        textareaRef.current.value = '';
        textareaRef.current.style.height = 'auto';
      }
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleChange = (e: ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.currentTarget.value;
    setLength(value.length);

    // Auto-resize textarea
    e.currentTarget.style.height = 'auto';
    e.currentTarget.style.height = Math.min(e.currentTarget.scrollHeight, 150) + 'px';
  };

  useEffect(() => {
    if (textareaRef.current && !disabled) {
      textareaRef.current.focus();
    }
  }, [disabled]);

  return (
    <div className="border-t border-border-subtle bg-warm-bg px-4 py-4">
      <div className="mx-auto flex max-w-4xl flex-col gap-2">
        <div className="flex gap-3">
          <textarea
            ref={textareaRef}
            data-testid="chat-input"
            placeholder="Type a message... (Enter to send, Shift+Enter for newline)"
            onKeyDown={handleKeyDown}
            onChange={handleChange}
            disabled={disabled}
            maxLength={MAX_LENGTH}
            className="flex-1 resize-none rounded-lg border border-border-subtle bg-white px-3 py-2 text-ink placeholder-ink-muted focus:outline-none focus:ring-2 focus:ring-signal-green disabled:bg-warm-surface disabled:text-ink-muted"
            rows={1}
          />
          <button
            data-testid="send-button"
            onClick={handleSend}
            disabled={disabled || !length}
            className="self-end rounded-lg bg-signal-green px-4 py-2 font-medium text-white hover:bg-signal-green/90 disabled:bg-ink-muted focus:outline-none focus:ring-2 focus:ring-signal-green focus:ring-offset-2"
            aria-label="Send message"
          >
            Send
          </button>
        </div>
        <div className="text-right text-xs text-ink-muted">
          {length} / {MAX_LENGTH}
        </div>
      </div>
    </div>
  );
}
