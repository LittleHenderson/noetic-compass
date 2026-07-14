import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import {
  decodeAccountToken,
  fetchPublicAccountCapabilities,
  loginAccount,
  logoutAccount,
  redeemAccountInvite,
  resolveAccountApiBaseUrl,
  rotateOwnAccountCredential,
  type AccountAuthApiOptions,
  type AccountCredentialRotationResponse,
  type AccountJwtClaims,
  type AccountPublicProfile,
} from '../lib/accountAuthApi';

export const ACCOUNT_SESSION_STORAGE_KEY = 'cas_harness.account.jwt.v1';
export const LEGACY_LIVE_INVITE_STORAGE_KEY = 'atlas_live_invite_code';
export const ACCOUNT_CAPABILITY_TIMEOUT_MS = 10_000;

export interface CredentialHandoff {
  credential: string;
  reason: 'rotation';
  issuedAt: string;
}

export interface AccountAuthContextValue {
  accountsEnabled: boolean;
  token: string | null;
  claims: AccountJwtClaims | null;
  isAuthenticated: boolean;
  credentialHandoff: CredentialHandoff | null;
  logoutWarning: string | null;
  login: (username: string, apiCredential: string) => Promise<AccountJwtClaims>;
  redeemInvite: (input: {
    code: string;
    emailOrUsername: string;
    apiCredential: string;
    displayName?: string | null;
  }) => Promise<AccountPublicProfile>;
  logout: () => Promise<void>;
  rotateCredential: (apiCredential: string) => Promise<AccountCredentialRotationResponse>;
  clearCredentialHandoff: () => void;
  clearLogoutWarning: () => void;
  authenticatedFetch: typeof fetch;
}

const unavailable = async (): Promise<never> => {
  throw new Error('AccountAuthProvider is not installed.');
};

const defaultContext: AccountAuthContextValue = {
  accountsEnabled: false,
  token: null,
  claims: null,
  isAuthenticated: false,
  credentialHandoff: null,
  logoutWarning: null,
  login: unavailable,
  redeemInvite: unavailable,
  logout: unavailable,
  rotateCredential: unavailable,
  clearCredentialHandoff: () => undefined,
  clearLogoutWarning: () => undefined,
  authenticatedFetch: ((input: RequestInfo | URL, init?: RequestInit) =>
    globalThis.fetch(input, init)) as typeof fetch,
};

const AccountAuthContext = createContext<AccountAuthContextValue>(defaultContext);

function requestUrl(input: RequestInfo | URL): string {
  if (typeof input === 'string') return input;
  if (input instanceof URL) return input.toString();
  return input.url;
}

export function mayAttachAccountBearer(
  input: RequestInfo | URL,
  accountApiBaseUrl: string = resolveAccountApiBaseUrl(),
): boolean {
  const browserOrigin = globalThis.location?.origin || 'http://localhost';
  let target: URL;
  try {
    target = new URL(requestUrl(input), browserOrigin);
  } catch {
    return false;
  }

  const sameOriginApi =
    target.origin === browserOrigin &&
    (target.pathname === '/api' || target.pathname.startsWith('/api/'));
  if (sameOriginApi) return true;

  // Production Atlas builds call the API on a separate, explicitly configured
  // origin. Only that exact origin is trusted; paths on arbitrary BYO/provider
  // origins never receive the CAS account Bearer.
  if (!/^https?:\/\//i.test(accountApiBaseUrl)) return false;
  try {
    return target.origin === new URL(accountApiBaseUrl).origin;
  } catch {
    return false;
  }
}

export interface AccountAuthProviderProps {
  children: ReactNode;
  apiOptions?: AccountAuthApiOptions;
  accountsEnabled?: boolean;
}

type AccountCapabilityState =
  | { status: 'loading' }
  | { status: 'ready'; accountsEnabled: boolean }
  | { status: 'error'; reason: 'mismatch' | 'unavailable' };

export function resolveAccountsEnabled(explicit?: boolean): boolean {
  if (typeof explicit === 'boolean') return explicit;
  return import.meta.env?.VITE_ACCOUNTS_ENABLED?.trim() === 'true';
}

function readRestoredToken(): string | null {
  try {
    const candidate = globalThis.sessionStorage?.getItem(ACCOUNT_SESSION_STORAGE_KEY)?.trim();
    if (!candidate) return null;
    if (decodeAccountToken(candidate)) return candidate;
    globalThis.sessionStorage.removeItem(ACCOUNT_SESSION_STORAGE_KEY);
  } catch {
    // Storage can be unavailable in locked-down browser contexts. The provider
    // remains usable for the current render, without falling back to localStorage.
  }
  return null;
}

export function AccountAuthProvider({
  children,
  apiOptions,
  accountsEnabled: accountsEnabledOverride,
}: AccountAuthProviderProps): JSX.Element {
  const configuredAccountsEnabled = resolveAccountsEnabled(accountsEnabledOverride);
  const [capabilityState, setCapabilityState] = useState<AccountCapabilityState>({
    status: 'loading',
  });
  const accountsEnabled = capabilityState.status === 'ready'
    ? capabilityState.accountsEnabled
    : false;
  // Restoring a browser JWT is intentionally deferred until the unauthenticated
  // server capability agrees with the Atlas build flag.
  const [token, setToken] = useState<string | null>(null);
  const [credentialHandoff, setCredentialHandoff] = useState<CredentialHandoff | null>(null);
  const [logoutWarning, setLogoutWarning] = useState<string | null>(null);
  const claims = useMemo(() => (token ? decodeAccountToken(token) : null), [token]);

  const clearSession = useCallback(() => {
    setToken(null);
    try {
      globalThis.sessionStorage?.removeItem(ACCOUNT_SESSION_STORAGE_KEY);
    } catch {
      // The in-memory state is still cleared when storage access is denied.
    }
    try {
      // Remove the legacy cockpit credential persisted by older builds. New
      // builds keep this value only in CockpitPage memory.
      globalThis.localStorage?.removeItem(LEGACY_LIVE_INVITE_STORAGE_KEY);
    } catch {
      // Locked-down contexts may deny storage access; no new secret is written.
    }
  }, []);

  useEffect(() => {
    let active = true;
    const controller = new AbortController();
    const upstreamSignal = apiOptions?.signal;
    const abortFromUpstream = () => controller.abort();
    if (upstreamSignal?.aborted) {
      controller.abort();
    } else {
      upstreamSignal?.addEventListener('abort', abortFromUpstream, { once: true });
    }

    setCapabilityState({ status: 'loading' });
    let timeoutId: ReturnType<typeof setTimeout> | undefined;
    const deadline = new Promise<never>((_resolve, reject) => {
      timeoutId = setTimeout(() => {
        controller.abort();
        reject(new Error('Account capability verification timed out.'));
      }, ACCOUNT_CAPABILITY_TIMEOUT_MS);
    });
    void Promise.race([fetchPublicAccountCapabilities({
      baseUrl: apiOptions?.baseUrl,
      fetchImpl: apiOptions?.fetchImpl,
      signal: controller.signal,
    }), deadline]).then((capabilities) => {
      if (!active) return;
      if (capabilities.accounts_enabled !== configuredAccountsEnabled) {
        clearSession();
        setCapabilityState({ status: 'error', reason: 'mismatch' });
        return;
      }
      if (capabilities.accounts_enabled) {
        setToken(readRestoredToken());
      } else {
        clearSession();
      }
      setCapabilityState({
        status: 'ready',
        accountsEnabled: capabilities.accounts_enabled,
      });
    }).catch(() => {
      if (!active) return;
      clearSession();
      setCapabilityState({ status: 'error', reason: 'unavailable' });
    }).finally(() => {
      if (timeoutId !== undefined) clearTimeout(timeoutId);
    });

    return () => {
      active = false;
      if (timeoutId !== undefined) clearTimeout(timeoutId);
      upstreamSignal?.removeEventListener('abort', abortFromUpstream);
      controller.abort();
    };
  }, [
    apiOptions?.baseUrl,
    apiOptions?.fetchImpl,
    apiOptions?.signal,
    clearSession,
    configuredAccountsEnabled,
  ]);

  const installSession = useCallback((newToken: string): AccountJwtClaims => {
    const newClaims = decodeAccountToken(newToken);
    if (!newClaims) throw new Error('Account login returned an invalid or expired account token.');
    try {
      globalThis.sessionStorage?.setItem(ACCOUNT_SESSION_STORAGE_KEY, newToken);
    } catch {
      // The token remains memory-only if sessionStorage is unavailable. Never
      // fall back to localStorage, IndexedDB, cookies, or credential persistence.
    }
    setToken(newToken);
    setCredentialHandoff(null);
    setLogoutWarning(null);
    return newClaims;
  }, []);

  useEffect(() => {
    try {
      globalThis.localStorage?.removeItem(LEGACY_LIVE_INVITE_STORAGE_KEY);
    } catch {
      // Best-effort migration cleanup; current code never writes the key.
    }
  }, []);

  useEffect(() => {
    if (!claims) {
      if (token) clearSession();
      return;
    }
    const delay = Math.max(0, Math.min(claims.exp * 1000 - Date.now(), 2_147_000_000));
    const timeout = globalThis.setTimeout(clearSession, delay);
    return () => globalThis.clearTimeout(timeout);
  }, [claims, clearSession, token]);

  const login = useCallback(async (username: string, apiCredential: string) => {
    if (!accountsEnabled) throw new Error('Customer account mode is not enabled on this deployment.');
    const response = await loginAccount({ username, apiCredential }, apiOptions);
    return installSession(response.token);
  }, [accountsEnabled, apiOptions, installSession]);

  const redeemInvite = useCallback(async (input: {
    code: string;
    emailOrUsername: string;
    apiCredential: string;
    displayName?: string | null;
  }) => {
    if (!accountsEnabled) throw new Error('Customer account mode is not enabled on this deployment.');
    const account = await redeemAccountInvite(input, apiOptions);
    const response = await loginAccount({
      username: input.emailOrUsername,
      apiCredential: input.apiCredential,
    }, apiOptions);
    installSession(response.token);
    return account;
  }, [accountsEnabled, apiOptions, installSession]);

  const logout = useCallback(async () => {
    const activeToken = token;
    setLogoutWarning(null);
    try {
      if (activeToken) await logoutAccount(activeToken, apiOptions);
    } catch (caught) {
      setLogoutWarning(
        'Local sign-out completed, but server session revocation is unavailable. The prior session may remain active until it expires; contact the platform operator if the token may be exposed.',
      );
      throw caught;
    } finally {
      clearSession();
    }
  }, [apiOptions, clearSession, token]);

  const rotateCredential = useCallback(async (apiCredential: string) => {
    if (!accountsEnabled) throw new Error('Customer account mode is not enabled on this deployment.');
    if (!token) throw new Error('Sign in before rotating the account credential.');
    const response = await rotateOwnAccountCredential(token, apiCredential, apiOptions);
    setCredentialHandoff({
      credential: apiCredential,
      reason: 'rotation',
      issuedAt: response.credential_issued_at,
    });
    clearSession();
    return response;
  }, [accountsEnabled, apiOptions, clearSession, token]);

  const authenticatedFetch = useCallback<typeof fetch>(async (
    input: RequestInfo | URL,
    init?: RequestInit,
  ) => {
    const fetchImpl = apiOptions?.fetchImpl ?? globalThis.fetch;
    if (!fetchImpl) throw new Error('Authenticated requests require fetch support.');
    const headers = new Headers(init?.headers);
    const accountApiBaseUrl = resolveAccountApiBaseUrl(apiOptions?.baseUrl);
    const attachedAccountBearer = Boolean(
      token && mayAttachAccountBearer(input, accountApiBaseUrl),
    );
    if (attachedAccountBearer) {
      headers.set('Authorization', `Bearer ${token}`);
    } else {
      // Strip even a stale inherited Authorization header on untrusted origins.
      headers.delete('Authorization');
    }
    const response = await fetchImpl(input, { ...init, headers });
    if (response.status === 401 && attachedAccountBearer) clearSession();
    return response;
  }, [apiOptions?.baseUrl, apiOptions?.fetchImpl, clearSession, token]);

  const value = useMemo<AccountAuthContextValue>(() => ({
    accountsEnabled,
    token,
    claims,
    isAuthenticated: claims !== null,
    credentialHandoff,
    logoutWarning,
    login,
    redeemInvite,
    logout,
    rotateCredential,
    clearCredentialHandoff: () => setCredentialHandoff(null),
    clearLogoutWarning: () => setLogoutWarning(null),
    authenticatedFetch,
  }), [
    accountsEnabled,
    authenticatedFetch,
    claims,
    credentialHandoff,
    login,
    logoutWarning,
    logout,
    redeemInvite,
    rotateCredential,
    token,
  ]);

  if (capabilityState.status === 'loading') {
    return (
      <div
        role="status"
        aria-live="polite"
        data-account-capability-state="loading"
      >
        Verifying customer account mode…
      </div>
    );
  }
  if (capabilityState.status === 'error') {
    return (
      <div
        role="alert"
        data-account-capability-state={capabilityState.reason}
      >
        Customer account mode could not be verified. Please try again later.
      </div>
    );
  }

  return <AccountAuthContext.Provider value={value}>{children}</AccountAuthContext.Provider>;
}

export function useAccountAuth(): AccountAuthContextValue {
  return useContext(AccountAuthContext);
}

export default AccountAuthProvider;
