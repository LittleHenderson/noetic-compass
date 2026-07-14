const DEFAULT_ACCOUNT_API_BASE_URL = '/api';
export const ACCOUNT_CAPABILITIES_PATH = '/public/capabilities';
const MAX_ACCOUNT_CAPABILITIES_RESPONSE_BYTES = 256;
const ACCOUNT_CREDENTIAL_PREFIX = 'casak_';
const ACCOUNT_CREDENTIAL_BYTES = 32;

export interface AccountAuthApiOptions {
  baseUrl?: string;
  fetchImpl?: typeof fetch;
  signal?: AbortSignal;
}

export interface AccountTokenResponse {
  token: string;
  expires_in_minutes: number;
}

export interface AccountPublicProfile {
  account_id: string;
  email_or_username: string;
  role: string;
  tenant_id: string;
  status: string;
  display_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface AccountCredentialRotationResponse {
  rotated: boolean;
  credential_issued_at: string;
}

export interface PublicAccountCapabilities {
  accounts_enabled: boolean;
}

export interface AccountJwtClaims {
  sub: string;
  account_id: string;
  tenant_id: string;
  role: string;
  jti: string;
  exp: number;
}

export class AccountAuthApiError extends Error {
  readonly httpStatus?: number;
  readonly detail?: string;

  constructor(
    message: string,
    options?: { httpStatus?: number; detail?: string; cause?: unknown },
  ) {
    super(message);
    this.name = 'AccountAuthApiError';
    this.httpStatus = options?.httpStatus;
    this.detail = options?.detail;
    if (options?.cause !== undefined) {
      (this as Error & { cause?: unknown }).cause = options.cause;
    }
  }
}

export function resolveAccountApiBaseUrl(explicit?: string): string {
  if (explicit?.trim()) return trimTrailingSlash(explicit.trim());

  const configured = import.meta.env?.VITE_ATLAS_API_BASE_URL?.trim();
  if (!configured) return DEFAULT_ACCOUNT_API_BASE_URL;

  const trimmed = trimTrailingSlash(configured);
  if (trimmed === '/api/atlas') return '/api';
  if (trimmed === '/atlas') return '/api';

  for (const suffix of ['/api/atlas', '/atlas']) {
    if (trimmed.endsWith(suffix)) return trimmed.slice(0, -suffix.length);
  }
  return trimmed;
}

/** Build the one trusted capability URL without accepting scheme-relative or credentialed bases. */
export function resolveAccountCapabilityUrl(explicit?: string): string {
  const base = resolveAccountApiBaseUrl(explicit);
  if (base.startsWith('/')) {
    if (base.startsWith('//') || base.includes('\\') || /[?#]/.test(base)) {
      throw new AccountAuthApiError('Account API base URL is invalid.');
    }
    return `${base}${ACCOUNT_CAPABILITIES_PATH}`;
  }

  let parsed: URL;
  try {
    parsed = new URL(base);
  } catch {
    throw new AccountAuthApiError('Account API base URL is invalid.');
  }
  if (
    !['http:', 'https:'].includes(parsed.protocol) ||
    parsed.username !== '' ||
    parsed.password !== '' ||
    parsed.search !== '' ||
    parsed.hash !== ''
  ) {
    throw new AccountAuthApiError('Account API base URL is invalid.');
  }
  if (globalThis.location?.protocol === 'https:' && parsed.protocol !== 'https:') {
    throw new AccountAuthApiError('Account API base URL is invalid.');
  }

  parsed.pathname = `${trimTrailingSlash(parsed.pathname)}${ACCOUNT_CAPABILITIES_PATH}`;
  return parsed.toString();
}

/**
 * Read the secret-free account-mode handshake from the exact configured API
 * base. This request is deliberately anonymous even when a prior account JWT
 * exists in browser storage: no Bearer, cookie, redirect, or referrer is sent.
 */
export async function fetchPublicAccountCapabilities(
  options?: AccountAuthApiOptions,
): Promise<PublicAccountCapabilities> {
  const fetchImpl = options?.fetchImpl ?? globalThis.fetch;
  if (!fetchImpl) {
    throw new AccountAuthApiError('Account capability verification requires fetch support.');
  }

  const requestUrl = resolveAccountCapabilityUrl(options?.baseUrl);
  let response: Response;
  try {
    response = await fetchImpl(requestUrl, {
      method: 'GET',
      headers: {
        Accept: 'application/json',
      },
      cache: 'no-store',
      credentials: 'omit',
      redirect: 'error',
      referrerPolicy: 'no-referrer',
      signal: options?.signal,
    });
  } catch (cause) {
    throw new AccountAuthApiError('Account capability verification is unavailable.', {
      detail: cause instanceof Error ? cause.message : String(cause),
      cause,
    });
  }
  if (!response.ok) {
    throw new AccountAuthApiError('Account capability verification is unavailable.', {
      httpStatus: response.status,
    });
  }

  const contentType = response.headers.get('Content-Type')
    ?.split(';', 1)[0]
    .trim()
    .toLowerCase();
  if (contentType !== 'application/json') {
    throw new AccountAuthApiError('Account capability response was malformed.');
  }
  const declaredLength = Number(response.headers.get('Content-Length'));
  if (
    Number.isFinite(declaredLength) &&
    declaredLength > MAX_ACCOUNT_CAPABILITIES_RESPONSE_BYTES
  ) {
    throw new AccountAuthApiError('Account capability response was malformed.');
  }

  let serialized: string;
  try {
    serialized = await response.text();
  } catch (cause) {
    throw new AccountAuthApiError('Account capability response was malformed.', { cause });
  }
  if (new TextEncoder().encode(serialized).byteLength > MAX_ACCOUNT_CAPABILITIES_RESPONSE_BYTES) {
    throw new AccountAuthApiError('Account capability response was malformed.');
  }
  const exactContract = serialized.match(
    /^\s*\{\s*"accounts_enabled"\s*:\s*(true|false)\s*\}\s*$/,
  );
  if (!exactContract) {
    throw new AccountAuthApiError('Account capability response was malformed.');
  }
  return { accounts_enabled: exactContract[1] === 'true' };
}

/**
 * Create the client-held account credential accepted by the hardened backend.
 * The credential is generated from 256 random bits and is never sent anywhere
 * except the account endpoint selected by the caller.
 */
export function generateAccountCredential(
  cryptoImpl: Pick<Crypto, 'getRandomValues'> | undefined = globalThis.crypto,
): string {
  if (!cryptoImpl?.getRandomValues) {
    throw new AccountAuthApiError(
      'Secure credential generation requires Web Crypto support.',
    );
  }
  const bytes = new Uint8Array(ACCOUNT_CREDENTIAL_BYTES);
  cryptoImpl.getRandomValues(bytes);
  const binary = String.fromCharCode(...bytes);
  const encoded = globalThis.btoa(binary)
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/g, '');
  return `${ACCOUNT_CREDENTIAL_PREFIX}${encoded}`;
}

export async function loginAccount(
  input: { username: string; apiCredential: string },
  options?: AccountAuthApiOptions,
): Promise<AccountTokenResponse> {
  const response = await requestJson('/auth/token', {
    method: 'POST',
    headers: jsonHeaders(),
    body: JSON.stringify({
      username: input.username.trim(),
      api_credential: input.apiCredential.trim(),
    }),
    signal: options?.signal,
  }, options);
  return parseTokenResponse(response);
}

export async function redeemAccountInvite(
  input: {
    code: string;
    emailOrUsername: string;
    apiCredential: string;
    displayName?: string | null;
  },
  options?: AccountAuthApiOptions,
): Promise<AccountPublicProfile> {
  const response = await requestJson('/accounts/invite/redeem', {
    method: 'POST',
    headers: jsonHeaders(),
    body: JSON.stringify({
      code: input.code.trim(),
      email_or_username: input.emailOrUsername.trim(),
      api_credential: input.apiCredential.trim(),
      display_name: input.displayName?.trim() || null,
    }),
    signal: options?.signal,
  }, options);
  return parseAccountProfile(response);
}

export async function logoutAccount(
  authToken: string,
  options?: AccountAuthApiOptions,
): Promise<{ revoked: boolean }> {
  const response = await requestJson('/auth/logout', {
    method: 'POST',
    headers: authHeaders(authToken),
    signal: options?.signal,
  }, options);
  if (!isRecord(response) || response.revoked !== true) {
    throw new AccountAuthApiError('Account logout response was malformed.');
  }
  return { revoked: true };
}

export async function rotateOwnAccountCredential(
  authToken: string,
  apiCredential: string,
  options?: AccountAuthApiOptions,
): Promise<AccountCredentialRotationResponse> {
  const response = await requestJson('/accounts/credential/rotate', {
    method: 'POST',
    headers: { ...jsonHeaders(), ...authHeaders(authToken) },
    body: JSON.stringify({ api_credential: apiCredential.trim() }),
    signal: options?.signal,
  }, options);
  if (
    !isRecord(response) ||
    response.rotated !== true ||
    typeof response.credential_issued_at !== 'string' ||
    !response.credential_issued_at
  ) {
    throw new AccountAuthApiError('Account credential rotation response was malformed.');
  }
  return {
    rotated: true,
    credential_issued_at: response.credential_issued_at,
  };
}

export function decodeAccountToken(
  token: string,
  nowMs: number = Date.now(),
): AccountJwtClaims | null {
  const parts = token.trim().split('.');
  if (parts.length !== 3) return null;
  try {
    const payload = JSON.parse(decodeBase64Url(parts[1])) as unknown;
    if (!isRecord(payload)) return null;
    const claims: AccountJwtClaims = {
      sub: requiredString(payload.sub),
      account_id: requiredString(payload.account_id),
      tenant_id: requiredString(payload.tenant_id),
      role: requiredString(payload.role),
      jti: requiredString(payload.jti),
      exp: requiredFiniteNumber(payload.exp),
    };
    if (claims.exp * 1000 <= nowMs) return null;
    return claims;
  } catch {
    return null;
  }
}

async function requestJson(
  path: string,
  init: RequestInit,
  options?: AccountAuthApiOptions,
): Promise<unknown> {
  const fetchImpl = options?.fetchImpl ?? globalThis.fetch;
  if (!fetchImpl) {
    throw new AccountAuthApiError('Account authentication requires fetch support.');
  }

  let response: Response;
  try {
    response = await fetchImpl(`${resolveAccountApiBaseUrl(options?.baseUrl)}${path}`, init);
  } catch (cause) {
    throw new AccountAuthApiError('Account request failed before a response.', {
      detail: cause instanceof Error ? cause.message : String(cause),
      cause,
    });
  }
  if (!response.ok) {
    const detail = await readErrorDetail(response);
    throw new AccountAuthApiError(detail, {
      httpStatus: response.status,
      detail,
    });
  }
  try {
    return await response.json();
  } catch (cause) {
    throw new AccountAuthApiError('Account API returned invalid JSON.', { cause });
  }
}

function parseTokenResponse(raw: unknown): AccountTokenResponse {
  if (
    !isRecord(raw) ||
    typeof raw.token !== 'string' ||
    !raw.token ||
    typeof raw.expires_in_minutes !== 'number' ||
    !Number.isFinite(raw.expires_in_minutes) ||
    raw.expires_in_minutes <= 0
  ) {
    throw new AccountAuthApiError('Account login response was malformed.');
  }
  if (!decodeAccountToken(raw.token)) {
    throw new AccountAuthApiError('Account login returned an invalid or expired account token.');
  }
  return { token: raw.token, expires_in_minutes: raw.expires_in_minutes };
}

function parseAccountProfile(raw: unknown): AccountPublicProfile {
  if (!isRecord(raw)) {
    throw new AccountAuthApiError('Invite redemption response was malformed.');
  }
  return {
    account_id: requiredString(raw.account_id),
    email_or_username: requiredString(raw.email_or_username),
    role: requiredString(raw.role),
    tenant_id: requiredString(raw.tenant_id),
    status: requiredString(raw.status),
    display_name: typeof raw.display_name === 'string' ? raw.display_name : null,
    created_at: requiredString(raw.created_at),
    updated_at: requiredString(raw.updated_at),
  };
}

function jsonHeaders(): Record<string, string> {
  return {
    Accept: 'application/json',
    'Content-Type': 'application/json',
    'Cache-Control': 'no-store',
  };
}

function authHeaders(token: string): Record<string, string> {
  const cleaned = token.trim().replace(/^Bearer\s+/i, '');
  return {
    Accept: 'application/json',
    Authorization: `Bearer ${cleaned}`,
    'Cache-Control': 'no-store',
  };
}

async function readErrorDetail(response: Response): Promise<string> {
  try {
    const body = await response.json() as unknown;
    if (isRecord(body) && typeof body.detail === 'string' && body.detail.trim()) {
      return body.detail.trim();
    }
  } catch {
    // Fall through to the status-only message.
  }
  return response.statusText || `Account API returned HTTP ${response.status}.`;
}

function decodeBase64Url(value: string): string {
  const base64 = value.replace(/-/g, '+').replace(/_/g, '/');
  const padded = `${base64}${'='.repeat((4 - (base64.length % 4)) % 4)}`;
  const bytes = Uint8Array.from(globalThis.atob(padded), (character) => character.charCodeAt(0));
  return new TextDecoder().decode(bytes);
}

function requiredString(value: unknown): string {
  if (typeof value === 'string' && value.trim()) return value;
  throw new Error('required string');
}

function requiredFiniteNumber(value: unknown): number {
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  throw new Error('required number');
}

function trimTrailingSlash(value: string): string {
  return value.endsWith('/') ? value.slice(0, -1) : value;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}
