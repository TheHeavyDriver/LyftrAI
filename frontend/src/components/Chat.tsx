import { useState, useCallback, useRef } from 'react';
import { Message, ChatResponse } from '../types';
import { generateSessionId } from '../utils';
import { apiClient } from '../api';
import { Header } from './Header';
import { ChatTranscript } from './ChatTranscript';
import { UserBubble } from './UserBubble';
import { AssistantBubble } from './AssistantBubble';
import { LoadingIndicator } from './LoadingIndicator';
import { ErrorMessage } from './ErrorMessage';
import { ChatComposer } from './ChatComposer';
import { SystemPromptPanel } from './SystemPromptPanel';

export function Chat() {
  const [sessionId] = useState(() => generateSessionId());
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [systemPrompt, setSystemPrompt] = useState('');
  const retryMessageRef = useRef<string | null>(null);

  const handleSendMessage = useCallback(
    async (message: string) => {
      if (!message.trim()) return;

      retryMessageRef.current = message;
      setError(null);

      // Add optimistic user message
      setMessages((prev) => [...prev, { role: 'user', content: message }]);
      setLoading(true);

      try {
        const response: ChatResponse = await apiClient.chat({
          session_id: sessionId,
          message: message.trim(),
          system_prompt: systemPrompt || undefined,
        });

        setMessages((prev) => [
          ...prev,
          {
            role: 'assistant',
            content: response.reply,
            metadata: response.metadata,
          },
        ]);
        retryMessageRef.current = null;
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : 'Failed to get response';
        setError(errorMessage);

        // Remove the optimistic message on error
        setMessages((prev) => prev.slice(0, -1));
      } finally {
        setLoading(false);
      }
    },
    [sessionId, systemPrompt]
  );

  const handleRetry = useCallback(() => {
    if (retryMessageRef.current) {
      handleSendMessage(retryMessageRef.current);
    }
  }, [handleSendMessage]);

  const handleSystemPromptChange = (prompt: string) => {
    setSystemPrompt(prompt);
  };

  return (
    <div className="flex h-screen flex-col bg-warm-bg">
      <Header sessionId={sessionId} />

      <ChatTranscript>
        {messages.map((msg, idx) => (
          <div key={idx}>
            {msg.role === 'user' ? (
              <UserBubble content={msg.content} />
            ) : (
              <AssistantBubble message={msg} />
            )}
          </div>
        ))}
        {loading && <LoadingIndicator />}
        {error && <ErrorMessage error={error} onRetry={handleRetry} />}
      </ChatTranscript>

      <SystemPromptPanel
        onSystemPromptChange={handleSystemPromptChange}
        disabled={loading}
      />

      <ChatComposer onSend={handleSendMessage} disabled={loading} />
    </div>
  );
}
