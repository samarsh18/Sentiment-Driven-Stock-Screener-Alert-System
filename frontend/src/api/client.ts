/**
 * frontend/src/api/client.ts
 * Centralized typed API client supporting both Real FastAPI endpoints & Mock Fallback.
 */

const RAW_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';
// Ensure no trailing slash on base URL
export const API_BASE_URL = RAW_BASE_URL.replace(/\/+$/, '');
export const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true';

export class ApiError extends Error {
  status: number;
  code?: string;
  details?: unknown;

  constructor(message: string, status: number, code?: string, details?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

export async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  const url = `${API_BASE_URL}${cleanEndpoint}`;

  const headers = new Headers(options.headers || {});
  if (!headers.has('Content-Type') && options.body && typeof options.body === 'string') {
    headers.set('Content-Type', 'application/json');
  }

  try {
    const response = await fetch(url, { ...options, headers });

    if (response.status === 204) {
      return {} as T;
    }

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      const errorMessage =
        data.detail || data.message || `API request failed with status ${response.status}`;
      throw new ApiError(errorMessage, response.status, data.code, data);
    }

    return data as T;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    // Network / server connection error
    throw new ApiError(
      'Backend API unavailable. Make sure FastAPI server is running on http://localhost:8000',
      0,
      'NETWORK_ERROR'
    );
  }
}
