import { ChatMetadata } from '../types';
import { formatLatency } from '../utils';

interface MetadataDisplayProps {
  metadata: ChatMetadata;
}

export function MetadataDisplay({ metadata }: MetadataDisplayProps) {
  const isCached = metadata.resolution_source === 'LLM_CACHE';

  return (
    <div className="mt-2 flex flex-wrap gap-3 text-xs text-ink-muted font-mono">
      <div
        data-testid="meta-source"
        className={`px-2 py-1 rounded ${
          isCached
            ? 'bg-signal-green/10 text-signal-green font-medium'
            : 'bg-warm-surface text-ink-muted'
        }`}
      >
        {metadata.resolution_source}
      </div>
      <div className="flex items-center gap-4">
        <span data-testid="meta-model" title="Model">
          {metadata.model}
        </span>
        <span data-testid="meta-latency" title="Latency">
          {formatLatency(metadata.latency_ms)}
        </span>
        <span data-testid="meta-input-tokens" title="Input tokens">
          ↑ {metadata.input_tokens}
        </span>
        <span data-testid="meta-output-tokens" title="Output tokens">
          ↓ {metadata.output_tokens}
        </span>
      </div>
    </div>
  );
}
