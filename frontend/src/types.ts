export interface ChatMetadata {
  resolution_source: 'LIVE_INFERENCE' | 'LLM_CACHE';
  model: string;
  latency_ms: number;
  input_tokens: number;
  output_tokens: number;
  key_id: string | null;
  fallback_attempts: number;
}

export interface AssistantMessage {
  role: 'assistant';
  content: string;
  metadata: ChatMetadata;
}

export interface UserMessage {
  role: 'user';
  content: string;
}

export type Message = UserMessage | AssistantMessage;

export interface ChatRequest {
  session_id: string;
  message: string;
  system_prompt?: string;
}

export interface ChatResponse {
  session_id: string;
  reply: string;
  metadata: ChatMetadata;
}

export interface ApiError {
  detail: string;
}
