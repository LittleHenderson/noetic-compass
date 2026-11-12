import { clearToken, getToken } from './auth';
import { API_BASE } from './config';

export class ApiError extends Error {
  status: number;
  detail: string;
  errorType: string;

  constructor(status: number, detail: string, errorType: string = 'api_error') {
    super(detail);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
    this.errorType = errorType;
  }
}

function stringifyDetail(detail: unknown, fallback: string): string {
  if (typeof detail === 'string') return detail;
  if (detail == null) return fallback;
  try {
    return JSON.stringify(detail);
  } catch {
    return fallback;
  }
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> | undefined),
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  } catch {
    throw new ApiError(
      0,
      `Unable to reach API at ${API_BASE}. Check the backend URL, deployment status, or browser cache state.`,
      'network_error',
    );
  }

  if (!res.ok) {
    let detail = res.statusText;
    let errorType = 'api_error';
    try {
      const body = await res.json();
      detail = stringifyDetail(body.detail, detail);
      errorType = body.error_type ?? errorType;
    } catch {
      // use statusText
    }
    if (res.status === 401) {
      clearToken();
      if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
        window.location.assign('/login');
      }
    }
    if (res.status === 429) {
      detail = 'Account limit reached. Your identity is unchanged. Wait for the limit to reset or contact the platform operator.';
    }
    throw new ApiError(res.status, detail, errorType);
  }

  return res.json() as Promise<T>;
}
