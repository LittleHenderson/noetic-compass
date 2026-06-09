export const ACCOUNT_SESSION_STORAGE_KEY = 'casHarnessAccountSession';

export interface AccountProfile {
  account_id: string;
  email_or_username: string;
  role: string;
  tenant_id: string;
  status: string;
  display_name?: string | null;
  created_at: string;
  updated_at: string;
}

export interface AccountSession {
  token: string;
  email: string;
  expiresAt: string | null;
  account: AccountProfile | null;
}

export interface AccountAuthRequestOptions {
  baseUrl?: string;
  fetchImpl?: typeof fetch;
}

export interface AccountLoginInput extends AccountAuthRequestOptions {
  email: string;
  inviteCode?: string | null;
  displayName?: string | null;
  mintSecret?: string | null;
}

interface TokenResponse {
  token: string;
  expires_in_minutes: number;
}

export class AccountAuthError extends Error {
  readonly httpStatus?: number;
  readonly detail?: string;

  constructor(message: string, opts?: { httpStatus?: number; detail?: string; cause?: unknown }) {
    super(message);
    this.name = 'AccountAuthError';
    this.httpStatus = opts?.httpStatus;
    this.detail = opts?.detail;
    if (opts?.cause !== undefined) {
      (this as Error & { cause?: unknown }).cause = opts.cause;
    }
  }
}

export async function loginOrRedeemAccount(input: AccountLoginInput): Promise<AccountSession> {
  const email = normalizeIdentity(input.email);
  const inviteCode = input.inviteCode?.trim() ?? '';
  const account = inviteCode
    ? await redeemInvite(
        {
          code: inviteCode,
          email,
          displayName: input.displayName,
        },
        input,
      )
    : null;
  const token = await mintAccountToken(
    {
      email,
      mintSecret: input.mintSecret,
    },
    input,
  );
  return {
    token: token.token,
    email,
    expiresAt: expiresAtFromMinutes(token.expires_in_minutes),
    account,
  };
}

export async function redeemInvite(
  input: {
    code: string;
    email: string;
    displayName?: string | null;
  },
  options?: AccountAuthRequestOptions,
): Promise<AccountProfile> {
  const code = input.code.trim();
  const email = normalizeIdentity(input.email);
  if (!code) {
    throw new AccountAuthError('Invite code is required to redeem an account.');
  }

  const response = await requestAccountJson('/accounts/invite/redeem', {
    method: 'POST',
    headers: jsonHeaders(),
    body: JSON.stringify({
      code,
      email_or_username: email,
      display_name: input.displayName?.trim() || undefined,
    }),
  }, options);
  return parseAccountProfile(response);
}

export async function mintAccountToken(
  input: { email: string; mintSecret?: string | null },
  options?: AccountAuthRequestOptions,
): Promise<TokenResponse> {
  const email = normalizeIdentity(input.email);
  const mintSecret = input.mintSecret?.trim() || import.meta.env?.VITE_AUTH_MINT_SECRET?.trim() || '';
  const headers = jsonHeaders();
  if (mintSecret) headers['X-Auth-Mint-Secret'] = mintSecret;

  const response = await requestAccountJson('/auth/token', {
    method: 'POST',
    headers,
    body: JSON.stringify({
      username: email,
      mint_secret: mintSecret || undefined,
    }),
  }, options);
  return parseTokenResponse(response);
}

export async function logoutAccountSession(
  token: string,
  options?: AccountAuthRequestOptions,
): Promise<void> {
  const authorization = authorizationHeaderValue(token);
  if (!authorization) return;
  await requestAccountJson('/auth/logout', {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      Authorization: authorization,
    },
  }, options);
}

export function readStoredAccountSession(
  storage: Storage | null = browserLocalStorage(),
): AccountSession | null {
  if (!storage) return null;
  const raw = storage.getItem(ACCOUNT_SESSION_STORAGE_KEY);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as unknown;
    return parseStoredSession(parsed);
  } catch {
    storage.removeItem(ACCOUNT_SESSION_STORAGE_KEY);
    return null;
  }
}

export function writeStoredAccountSession(
  session: AccountSession,
  storage: Storage | null = browserLocalStorage(),
): void {
  if (!storage) return;
  storage.setItem(ACCOUNT_SESSION_STORAGE_KEY, JSON.stringify(session));
}

export function clearStoredAccountSession(storage: Storage | null = browserLocalStorage()): void {
  storage?.removeItem(ACCOUNT_SESSION_STORAGE_KEY);
}

export function authorizationHeaderValue(token?: string | null): string | null {
  const trimmed = token?.trim();
  if (!trimmed) return null;
  return /^Bearer\s+/i.test(trimmed) ? trimmed : `Bearer ${trimmed}`;
}

export function resolveAccountApiBaseUrl(explicit?: string): string {
  if (explicit && explicit.length > 0) return trimTrailingSlash(explicit);

  const atlasBase = import.meta.env?.VITE_ATLAS_API_BASE_URL;
  if (typeof atlasBase === 'string' && atlasBase.length > 0) {
    return deriveAccountBaseUrlFromAtlasBase(atlasBase);
  }

  return '/api';
}

async function requestAccountJson(
  path: string,
  init: RequestInit,
  options?: AccountAuthRequestOptions,
): Promise<unknown> {
  const fetchImpl = options?.fetchImpl ?? (typeof fetch !== 'undefined' ? fetch : undefined);
  if (!fetchImpl) {
    throw new AccountAuthError('Account auth requires fetch support.');
  }

  let response: Response;
  try {
    response = await fetchImpl(`${resolveAccountApiBaseUrl(options?.baseUrl)}${path}`, init);
  } catch (error) {
    throw new AccountAuthError('Account auth request failed before a response.', {
      detail: error instanceof Error ? error.message : String(error),
      cause: error,
    });
  }

  let body: unknown = null;
  try {
    body = await response.json();
  } catch {
    body = null;
  }

  if (!response.ok) {
    const detail = responseDetail(body) ?? response.statusText;
    throw new AccountAuthError(detail || `Account auth returned HTTP ${response.status}.`, {
      httpStatus: response.status,
      detail,
    });
  }

  return body;
}

function parseTokenResponse(raw: unknown): TokenResponse {
  if (!isRecord(raw)) {
    throw new AccountAuthError('Account token response was malformed.');
  }
  return {
    token: requiredString(raw.token, 'token'),
    expires_in_minutes: requiredNumber(raw.expires_in_minutes, 'expires_in_minutes'),
  };
}

function parseAccountProfile(raw: unknown): AccountProfile {
  if (!isRecord(raw)) {
    throw new AccountAuthError('Account response was malformed.');
  }
  return {
    account_id: requiredString(raw.account_id, 'account_id'),
    email_or_username: requiredString(raw.email_or_username, 'email_or_username'),
    role: requiredString(raw.role, 'role'),
    tenant_id: requiredString(raw.tenant_id, 'tenant_id'),
    status: requiredString(raw.status, 'status'),
    display_name: nullableString(raw.display_name),
    created_at: requiredString(raw.created_at, 'created_at'),
    updated_at: requiredString(raw.updated_at, 'updated_at'),
  };
}

function parseStoredSession(raw: unknown): AccountSession | null {
  if (!isRecord(raw)) return null;
  const token = typeof raw.token === 'string' ? raw.token.trim() : '';
  const email = typeof raw.email === 'string' ? raw.email.trim() : '';
  if (!token || !email) return null;
  return {
    token,
    email,
    expiresAt: nullableString(raw.expiresAt),
    account: raw.account === null || raw.account === undefined ? null : parseAccountProfile(raw.account),
  };
}

function normalizeIdentity(email: string): string {
  const normalized = email.trim().toLowerCase();
  if (!normalized) {
    throw new AccountAuthError('Email is required.');
  }
  return normalized;
}

function jsonHeaders(): Record<string, string> {
  return {
    Accept: 'application/json',
    'Content-Type': 'application/json',
  };
}

function expiresAtFromMinutes(minutes: number): string | null {
  if (!Number.isFinite(minutes) || minutes <= 0) return null;
  return new Date(Date.now() + minutes * 60_000).toISOString();
}

function deriveAccountBaseUrlFromAtlasBase(atlasBase: string): string {
  const trimmed = trimTrailingSlash(atlasBase);
  if (trimmed === '/api/atlas') return '/api';
  if (trimmed.endsWith('/api/atlas')) {
    return trimmed.slice(0, -'/api/atlas'.length) || '/';
  }
  if (trimmed.endsWith('/atlas')) {
    return trimmed.slice(0, -'/atlas'.length) || '/';
  }
  if (trimmed.endsWith('/api')) return trimmed;
  return trimmed;
}

function responseDetail(raw: unknown): string | undefined {
  if (!isRecord(raw)) return undefined;
  const detail = raw.detail;
  if (typeof detail === 'string') return detail;
  if (detail !== undefined) return JSON.stringify(detail);
  return undefined;
}

function requiredString(raw: unknown, field: string): string {
  if (typeof raw === 'string' && raw.length > 0) return raw;
  throw new AccountAuthError(`Account response field "${field}" must be a non-empty string.`);
}

function requiredNumber(raw: unknown, field: string): number {
  if (typeof raw === 'number' && Number.isFinite(raw)) return raw;
  throw new AccountAuthError(`Account response field "${field}" must be a finite number.`);
}

function nullableString(raw: unknown): string | null {
  if (raw === null || raw === undefined) return null;
  return typeof raw === 'string' ? raw : null;
}

function trimTrailingSlash(url: string): string {
  return url.endsWith('/') ? url.slice(0, -1) : url;
}

function browserLocalStorage(): Storage | null {
  try {
    return typeof window !== 'undefined' ? window.localStorage : null;
  } catch {
    return null;
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}
