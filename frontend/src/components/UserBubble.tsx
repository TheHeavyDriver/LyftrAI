interface UserBubbleProps {
  content: string;
}

export function UserBubble({ content }: UserBubbleProps) {
  return (
    <div className="mb-4 flex justify-end">
      <div className="max-w-2xl rounded-lg bg-signal-green px-4 py-3 text-white">
        {content}
      </div>
    </div>
  );
}
