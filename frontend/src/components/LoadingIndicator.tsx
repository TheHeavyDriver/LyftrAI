export function LoadingIndicator() {
  return (
    <div className="mb-4 flex justify-start">
      <div className="max-w-2xl rounded-lg bg-warm-surface px-4 py-3 text-ink-muted">
        <div className="flex items-center gap-2">
          <div className="flex gap-1">
            <span className="animate-bounce animation-delay-0">●</span>
            <span className="animate-bounce animation-delay-200">●</span>
            <span className="animate-bounce animation-delay-400">●</span>
          </div>
        </div>
      </div>
    </div>
  );
}
