export function generateSessionId(): string {
  const chars = 'abcdefghijklmnopqrstuvwxyz0123456789';
  let id = 's-';
  for (let i = 0; i < 8; i++) {
    id += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return id;
}

export function formatLatency(ms: number): string {
  return `${ms} ms`;
}

export function truncateText(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength);
}
