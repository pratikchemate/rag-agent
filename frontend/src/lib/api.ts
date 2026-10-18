import {
  DocumentItem,
  DocumentPreview,
  ChatResponse,
  FeedbackRequest,
  FeedbackResponse,
} from '../types';

export const DEFAULT_PROD_API_URL = 'https://enterprise-knowledge-ai-api.onrender.com/api/v1';

export function resolveApiBaseUrl(): string {
  if (import.meta.env?.VITE_API_BASE_URL) {
    return import.meta.env.VITE_API_BASE_URL;
  }
  if (
    typeof window !== 'undefined' &&
    window.location.hostname !== 'localhost' &&
    window.location.hostname !== '127.0.0.1'
  ) {
    return DEFAULT_PROD_API_URL;
  }
  return '/api/v1';
}

export const API_BASE_URL = resolveApiBaseUrl();

export class ApiError extends Error {
  status: number;
  code: string;
  resetAt?: string;
  extra?: Record<string, unknown>;

  constructor(
    message: string,
    status: number,
    code: string = 'error',
    resetAt?: string,
    extra?: Record<string, unknown>
  ) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.resetAt = resetAt;
    this.extra = extra;
  }
}

export function cleanSignal(signal?: unknown): AbortSignal | undefined {
  return signal instanceof AbortSignal ? signal : undefined;
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (response.status === 204) {
    return {} as T;
  }

  const contentType = response.headers.get('content-type');
  const isJson = contentType && contentType.includes('application/json');
  const data = isJson ? await response.json() : await response.text();

  if (!response.ok) {
    if (typeof data === 'object' && data !== null) {
      const err = data as Record<string, any>;
      throw new ApiError(
        err.message || response.statusText || 'An error occurred',
        response.status,
        err.code || 'unknown_error',
        err.reset_at,
        err.extra
      );
    }
    throw new ApiError(
      typeof data === 'string' && data ? data : response.statusText,
      response.status,
      'http_error'
    );
  }

  return data as T;
}

function getHeaders(token?: string): HeadersInit {
  const headers: Record<string, string> = {};
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

export const api = {
  async checkHealth(signal?: unknown): Promise<{ status: string }> {
    const res = await fetch(`${API_BASE_URL}/health/live`, {
      signal: cleanSignal(signal),
    });
    return handleResponse<{ status: string }>(res);
  },

  async fetchDocuments(token?: string, signal?: unknown): Promise<DocumentItem[]> {
    const res = await fetch(`${API_BASE_URL}/documents`, {
      headers: getHeaders(token),
      signal: cleanSignal(signal),
    });
    return handleResponse<DocumentItem[]>(res);
  },

  async uploadDocument(
    file: File,
    token?: string,
    signal?: unknown
  ): Promise<{ document_id: string; status: string; filename: string }> {
    const formData = new FormData();
    formData.append('file', file);

    const res = await fetch(`${API_BASE_URL}/documents`, {
      method: 'POST',
      headers: getHeaders(token),
      body: formData,
      signal: cleanSignal(signal),
    });
    return handleResponse<{ document_id: string; status: string; filename: string }>(res);
  },

  async deleteDocument(id: string, token?: string, signal?: unknown): Promise<void> {
    const res = await fetch(`${API_BASE_URL}/documents/${id}`, {
      method: 'DELETE',
      headers: getHeaders(token),
      signal: cleanSignal(signal),
    });
    return handleResponse<void>(res);
  },

  async getDocumentPreview(
    id: string,
    token?: string,
    signal?: unknown
  ): Promise<DocumentPreview> {
    const res = await fetch(`${API_BASE_URL}/documents/${id}/preview`, {
      headers: getHeaders(token),
      signal: cleanSignal(signal),
    });
    return handleResponse<DocumentPreview>(res);
  },

  async sendChatMessage(
    question: string,
    documentIds: string[] | undefined,
    token?: string,
    signal?: unknown
  ): Promise<ChatResponse> {
    const res = await fetch(`${API_BASE_URL}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getHeaders(token),
      },
      signal: cleanSignal(signal),
      body: JSON.stringify({
        question,
        document_ids: documentIds && documentIds.length > 0 ? documentIds : undefined,
      }),
    });
    return handleResponse<ChatResponse>(res);
  },

  async submitFeedback(
    payload: FeedbackRequest,
    token?: string,
    signal?: unknown
  ): Promise<FeedbackResponse> {
    const res = await fetch(`${API_BASE_URL}/feedback`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getHeaders(token),
      },
      signal: cleanSignal(signal),
      body: JSON.stringify(payload),
    });
    return handleResponse<FeedbackResponse>(res);
  },
};
