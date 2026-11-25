import { useRef, useEffect, type ReactNode } from 'react';

interface ChatTranscriptProps {
  children: ReactNode;
}

export function ChatTranscript({ children }: ChatTranscriptProps) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [children]);

  return (
    <div
      className="flex-1 overflow-y-auto px-4 py-6"
      role="log"
      aria-label="Chat transcript"
    >
      {children}
      <div ref={endRef} />
    </div>
  );
}
