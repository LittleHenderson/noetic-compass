import { clearToken, getToken, setToken } from './auth';
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

function isMonthlyLimit(detail: string): boolean {
  return /monthly limit exceeded/i.test(detail);
}

function freshDashboardUsername(): string {
  const rand = Math.random().toString(36).slice(2, 8);
  return `dashboard-${Date.now().toString(36)}-${rand}`;
}

async function refreshDashboardToken(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/auth/token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: freshDashboardUsername() }),
    });
    if (!res.ok) return false;
    const data: { token?: string } = await res.json();
    if (!data.token) return false;
    setToken(data.token);
    return true;
  } catch {
    return false;
  }
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
  allowRecovery: boolean = true,
): Promise<T> {
  const res = await apiRequest(path, options, allowRecovery);
  return res.json() as Promise<T>;
}

export async function apiFetchText(
  path: string,
  options: RequestInit = {},
  allowRecovery: boolean = true,
): Promise<string> {
  const res = await apiRequest(path, options, allowRecovery);
  return res.text();
}

async function apiRequest(
  path: string,
  options: RequestInit = {},
  allowRecovery: boolean = true,
): Promise<Response> {
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
      if (allowRecovery && path !== '/auth/token' && await refreshDashboardToken()) {
        return apiRequest(path, options, false);
      }
      if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
        window.location.assign('/login');
      }
    }
    if (
      res.status === 429 &&
      allowRecovery &&
      path !== '/auth/token' &&
      isMonthlyLimit(detail) &&
      await refreshDashboardToken()
    ) {
      return apiRequest(path, options, false);
    }
    throw new ApiError(res.status, detail, errorType);
  }

  return res;
}
