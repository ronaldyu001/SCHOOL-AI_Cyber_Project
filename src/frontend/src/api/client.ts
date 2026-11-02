/**
 * Thin fetch wrapper over the dataset API.
 *
 * Requests go to a relative base so the Vite dev proxy (see vite.config.ts) can
 * forward them to the FastAPI service without the backend needing CORS.
 */

const BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? '/api';

const UNREACHABLE = 'Cannot reach the dataset API. Is the backend running on port 8000?';

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

/** FastAPI returns `{detail: string}` or `{detail: [{msg, loc}, ...]}` for 422s. */
function readDetail(payload: unknown, fallback: string): string {
  if (typeof payload !== 'object' || payload === null) return fallback;
  const detail = (payload as { detail?: unknown }).detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => (typeof item === 'object' && item !== null ? String((item as { msg?: unknown }).msg ?? '') : ''))
      .filter(Boolean);
    if (messages.length > 0) return messages.join('; ');
  }
  return fallback;
}

interface RequestOptions {
  method?: 'GET' | 'POST' | 'DELETE';
  body?: unknown;
  signal?: AbortSignal;
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, signal } = options;

  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      method,
      signal,
      headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error;
    throw new ApiError(0, UNREACHABLE);
  }

  if (response.status === 204) return undefined as T;

  const payload = await response.json().catch(() => null);

  if (!response.ok) {
    // 502/504 come from the dev proxy, not the API; 503 is the backend's own
    // "file could not be read" and keeps its detail.
    if (response.status === 502 || response.status === 504) {
      throw new ApiError(response.status, UNREACHABLE);
    }
    throw new ApiError(response.status, readDetail(payload, `Request failed with status ${response.status}`));
  }

  return payload as T;
}
