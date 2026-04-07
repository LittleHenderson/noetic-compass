import { getToken } from './auth';

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

  const res = await fetch(`/api${path}`, { ...options, headers });

  if (!res.ok) {
    let detail = res.statusText;
    let errorType = 'api_error';
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
      errorType = body.error_type ?? errorType;
    } catch {
      // use statusText
    }
    throw new ApiError(res.status, detail, errorType);
  }

  return res.json() as Promise<T>;
}
