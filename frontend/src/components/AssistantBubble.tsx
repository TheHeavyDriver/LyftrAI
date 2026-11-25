import { AssistantMessage } from '../types';
import { MetadataDisplay } from './MetadataDisplay';

interface AssistantBubbleProps {
  message: AssistantMessage;
}

export function AssistantBubble({ message }: AssistantBubbleProps) {
  return (
    <div
      data-testid="assistant-message"
      className="mb-4 flex justify-start"
    >
      <div className="max-w-2xl">
        <div className="rounded-lg bg-warm-surface px-4 py-3 text-ink">
          {message.content}
        </div>
        <MetadataDisplay metadata={message.metadata} />
      </div>
    </div>
  );
}
