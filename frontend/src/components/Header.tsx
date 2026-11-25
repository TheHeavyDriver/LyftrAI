interface HeaderProps {
  sessionId: string;
}

export function Header({ sessionId }: HeaderProps) {
  return (
    <header className="border-b border-border-subtle bg-warm-bg px-4 py-4" role="banner">
      <div className="mx-auto flex max-w-4xl items-center justify-between">
        <h1 className="text-2xl font-semibold text-ink">Lyftr AI</h1>
        <div className="flex items-center gap-2 text-sm text-ink-muted">
          <span className="font-mono">{sessionId}</span>
        </div>
      </div>
    </header>
  );
}
