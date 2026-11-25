import { ChatRequest, ChatResponse, ApiError } from './types';

const envBaseUrl = import.meta.env.VITE_API_BASE_URL;

// When no build-time URL is provided, talk to the backend on the same host the
// page was served from. This keeps localhost, 127.0.0.1, and LAN access working.
const API_BASE_URL =
  envBaseUrl || `${window.location.protocol}//${window.location.hostname}:8000`;

export class ApiClient {
  private baseUrl: string;
  private timeout: number = 30000;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  async health() {
    return this.get('/health');
  }

  async chat(payload: ChatRequest): Promise<ChatResponse> {
    return this.post('/chat', payload);
  }

  async getHistory(sessionId: string) {
    return this.get(`/sessions/${sessionId}/messages`);
  }

  private async get(path: string) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    try {
      const response = await fetch(`${this.baseUrl}${path}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        signal: controller.signal,
      });

      if (!response.ok) {
        const error = await this.parseError(response);
        throw error;
      }

      return response.json();
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        throw new Error('Request timeout');
      }
      throw error;
    } finally {
      clearTimeout(timeoutId);
    }
  }

  private async post(path: string, body: unknown, headers?: Record<string, string>) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    try {
      const response = await fetch(`${this.baseUrl}${path}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...headers,
        },
        body: JSON.stringify(body),
        signal: controller.signal,
      });

      if (!response.ok) {
        const error = await this.parseError(response);
        throw error;
      }

      return response.json();
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        throw new Error('Request timeout');
      }
      throw error;
    } finally {
      clearTimeout(timeoutId);
    }
  }

  private async parseError(response: Response): Promise<Error> {
    try {
      const data = (await response.json()) as ApiError;
      return new Error(data.detail || `HTTP ${response.status}`);
    } catch {
      return new Error(`HTTP ${response.status}`);
    }
  }
}

export const apiClient = new ApiClient();
