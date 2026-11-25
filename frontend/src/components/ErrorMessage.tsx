interface ErrorMessageProps {
  error: string;
  onRetry: () => void;
}

export function ErrorMessage({ error, onRetry }: ErrorMessageProps) {
  return (
    <div className="mb-4 flex justify-start">
      <div className="max-w-2xl rounded-lg border border-red-200 bg-red-50 px-4 py-3">
        <div className="mb-2 text-sm text-red-800">{error}</div>
        <button
          onClick={onRetry}
          className="text-sm text-red-600 underline hover:text-red-800 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
        >
          Retry
        </button>
      </div>
    </div>
  );
}
