import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
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
  resolveAccountCapabilityUrl,
  ACCOUNT_CAPABILITIES_PATH,
  rotateOwnAccountCredential,
  type AccountAuthApiOptions,
  type AccountCredentialRotationResponse,
  type AccountJwtClaims,
  type AccountPublicProfile,
} from '../lib/accountAuthApi';

export const ACCOUNT_SESSION_STORAGE_KEY = 'cas_harness.account.jwt.v1';
export const ACCOUNT_SESSION_API_KEY = 'cas_harness.account.api.v1';

export function accountSessionBinding(baseUrl?: string): string {
  const url = new URL(resolveAccountCapabilityUrl(baseUrl), globalThis.location?.origin || 'http://localhost');
  return url.href.slice(0, -ACCOUNT_CAPABILITIES_PATH.length);
}
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
  cancelPendingAuth: () => void;
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
  cancelPendingAuth: () => undefined,
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

  try {
    const base = new URL(accountApiBaseUrl, browserOrigin);
    if (!['http:', 'https:'].includes(base.protocol) || base.username || base.password ||
        base.search || base.hash || target.username || target.password) return false;
    const prefix = base.pathname.replace(/\/$/, '');
    return target.origin === base.origin &&
      (target.pathname === prefix || target.pathname.startsWith(`${prefix}/`));
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
  | { status: 'ready'; epoch: number; accountsEnabled: boolean; baseUrl?: string; fetchImpl?: typeof fetch; signal?: AbortSignal; configuredAccountsEnabled: boolean }
  | { status: 'error'; reason: 'mismatch' | 'unavailable' };

export function resolveAccountsEnabled(explicit?: boolean): boolean {
  if (typeof explicit === 'boolean') return explicit;
  return import.meta.env?.VITE_ACCOUNTS_ENABLED?.trim() === 'true';
}

function readRestoredToken(baseUrl?: string): string | null {
  try {
    const candidate = globalThis.sessionStorage?.getItem(ACCOUNT_SESSION_STORAGE_KEY)?.trim();
    if (!candidate) return null;
    if (globalThis.sessionStorage.getItem(ACCOUNT_SESSION_API_KEY) === accountSessionBinding(baseUrl) && decodeAccountToken(candidate)) return candidate;
    globalThis.sessionStorage.removeItem(ACCOUNT_SESSION_STORAGE_KEY);
    globalThis.sessionStorage.removeItem(ACCOUNT_SESSION_API_KEY);
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
  const verifiedBinding = capabilityState.status === 'ready' &&
    capabilityState.baseUrl === apiOptions?.baseUrl &&
    capabilityState.fetchImpl === apiOptions?.fetchImpl &&
    capabilityState.signal === apiOptions?.signal &&
    capabilityState.configuredAccountsEnabled === configuredAccountsEnabled;
  const accountsEnabled = verifiedBinding && capabilityState.accountsEnabled;
  // Restoring a browser JWT is intentionally deferred until the unauthenticated
  // server capability agrees with the Atlas build flag.
  const [token, setToken] = useState<string | null>(null);
  const [credentialHandoff, setCredentialHandoff] = useState<CredentialHandoff | null>(null);
  const [logoutWarning, setLogoutWarning] = useState<string | null>(null);
  const [quotaWarning, setQuotaWarning] = useState<string | null>(null);
  const tokenRef = useRef<string | null>(null);
  const accountModeReady = useRef(false);
  const bindingEpoch = useRef(0);
  const epoch = capabilityState.status === 'ready' ? capabilityState.epoch : 0;
  const assertCurrentBinding = useCallback(() => {
    if (!epoch || epoch !== bindingEpoch.current) {
      throw new Error('Account API binding changed. Please sign in again.');
    }
  }, [epoch]);
  const authOperation = useRef<{ generation: number; controller: AbortController | null }>({
    generation: 0, controller: null,
  });
  const cancelPendingAuth = useCallback(() => {
    authOperation.current.controller?.abort();
    authOperation.current = { generation: authOperation.current.generation + 1, controller: null };
  }, []);
  const beginAuthOperation = useCallback(() => {
    assertCurrentBinding();
    if (!accountsEnabled || !accountModeReady.current) throw new Error('Customer account mode is not enabled on this deployment.');
    cancelPendingAuth();
    const controller = new AbortController();
    const generation = authOperation.current.generation;
    authOperation.current.controller = controller;
    const upstream = apiOptions?.signal;
    const abort = () => controller.abort();
    if (upstream?.aborted) controller.abort();
    else upstream?.addEventListener('abort', abort, { once: true });
    return {
      options: { ...apiOptions, signal: controller.signal },
      assertCurrent: () => {
        assertCurrentBinding();
        if (controller.signal.aborted || generation !== authOperation.current.generation || !accountModeReady.current) {
          throw new Error('Account operation was cancelled. Please sign in again.');
        }
      },
      finish: () => upstream?.removeEventListener('abort', abort),
    };
  }, [accountsEnabled, apiOptions, assertCurrentBinding, cancelPendingAuth]);
  const claims = useMemo(() => (token ? decodeAccountToken(token) : null), [token]);

  const clearSession = useCallback(() => {
    cancelPendingAuth();
    tokenRef.current = null;
    setToken(null);
    setCredentialHandoff(null);
    setQuotaWarning(null);
    try {
      globalThis.sessionStorage?.removeItem(ACCOUNT_SESSION_STORAGE_KEY);
      globalThis.sessionStorage?.removeItem(ACCOUNT_SESSION_API_KEY);
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
  }, [cancelPendingAuth]);

  useEffect(() => {
    let active = true;
    const verificationEpoch = ++bindingEpoch.current;
    const controller = new AbortController();
    const upstreamSignal = apiOptions?.signal;
    const abortFromUpstream = () => controller.abort();
    if (upstreamSignal?.aborted) {
      controller.abort();
    } else {
      upstreamSignal?.addEventListener('abort', abortFromUpstream, { once: true });
    }

    accountModeReady.current = false;
    cancelPendingAuth();
    tokenRef.current = null;
    setToken(null);
    setCredentialHandoff(null);
    setLogoutWarning(null);
    setQuotaWarning(null);
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
      if (controller.signal.aborted) throw new Error('Account capability verification was cancelled.');
      if (capabilities.accounts_enabled !== configuredAccountsEnabled) {
        clearSession();
        setCapabilityState({ status: 'error', reason: 'mismatch' });
        return;
      }
      if (capabilities.accounts_enabled) {
        const restored = readRestoredToken(apiOptions?.baseUrl);
        tokenRef.current = restored;
        setToken(restored);
      } else {
        clearSession();
      }
      accountModeReady.current = capabilities.accounts_enabled;
      setCapabilityState({
        status: 'ready',
        epoch: verificationEpoch,
        accountsEnabled: capabilities.accounts_enabled,
        baseUrl: apiOptions?.baseUrl,
        fetchImpl: apiOptions?.fetchImpl,
        signal: apiOptions?.signal,
        configuredAccountsEnabled,
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
      bindingEpoch.current++;
      accountModeReady.current = false;
      cancelPendingAuth();
      if (timeoutId !== undefined) clearTimeout(timeoutId);
      upstreamSignal?.removeEventListener('abort', abortFromUpstream);
      controller.abort();
    };
  }, [
    apiOptions?.baseUrl,
    apiOptions?.fetchImpl,
    apiOptions?.signal,
    clearSession,
    cancelPendingAuth,
    configuredAccountsEnabled,
  ]);

  const installSession = useCallback((newToken: string): AccountJwtClaims => {
    const newClaims = decodeAccountToken(newToken);
    if (!newClaims) throw new Error('Account login returned an invalid or expired account token.');
    try {
      // Clear first so a partial storage failure cannot rebind an older JWT.
      globalThis.sessionStorage?.removeItem(ACCOUNT_SESSION_STORAGE_KEY);
      globalThis.sessionStorage?.removeItem(ACCOUNT_SESSION_API_KEY);
      globalThis.sessionStorage?.setItem(ACCOUNT_SESSION_API_KEY, accountSessionBinding(apiOptions?.baseUrl));
      globalThis.sessionStorage?.setItem(ACCOUNT_SESSION_STORAGE_KEY, newToken);
    } catch {
      // The token remains memory-only if sessionStorage is unavailable. Never
      // fall back to localStorage, IndexedDB, cookies, or credential persistence.
    }
    tokenRef.current = newToken;
    setToken(newToken);
    setQuotaWarning(null);
    setCredentialHandoff(null);
    setLogoutWarning(null);
    return newClaims;
  }, [apiOptions?.baseUrl]);

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
    const operation = beginAuthOperation();
    try {
      operation.assertCurrent();
      const response = await loginAccount({ username, apiCredential }, operation.options);
      operation.assertCurrent();
      return installSession(response.token);
    } finally {
      operation.finish();
    }
  }, [beginAuthOperation, installSession]);

  const redeemInvite = useCallback(async (input: {
    code: string;
    emailOrUsername: string;
    apiCredential: string;
    displayName?: string | null;
  }) => {
    const operation = beginAuthOperation();
    try {
      operation.assertCurrent();
      const account = await redeemAccountInvite(input, operation.options);
      operation.assertCurrent();
      const response = await loginAccount({
        username: input.emailOrUsername,
        apiCredential: input.apiCredential,
      }, operation.options);
      operation.assertCurrent();
      installSession(response.token);
      return account;
    } finally {
      operation.finish();
    }
  }, [beginAuthOperation, installSession]);

  const logout = useCallback(async () => {
    assertCurrentBinding();
    const activeToken = tokenRef.current;
    // Clear immediately, including any pending login. A delayed revocation must
    // never wipe out a newer, explicitly requested login.
    clearSession();
    setCredentialHandoff(null);
    setLogoutWarning(null);
    try {
      if (activeToken) await logoutAccount(activeToken, apiOptions);
    } catch (caught) {
      setLogoutWarning(
        'Local sign-out completed, but server session revocation is unavailable. The prior session may remain active until it expires; contact the platform operator if the token may be exposed.',
      );
      throw caught;
    }
  }, [apiOptions, assertCurrentBinding, clearSession]);

  const rotateCredential = useCallback(async (apiCredential: string) => {
    const operation = beginAuthOperation();
    try {
      operation.assertCurrent();
      const activeToken = tokenRef.current;
      if (!activeToken) throw new Error('Sign in before rotating the account credential.');
      const response = await rotateOwnAccountCredential(activeToken, apiCredential, operation.options);
      operation.assertCurrent();
      clearSession();
      setCredentialHandoff({
        credential: apiCredential,
        reason: 'rotation',
        issuedAt: response.credential_issued_at,
      });
      return response;
    } finally {
      operation.finish();
    }
  }, [beginAuthOperation, clearSession]);

  const authenticatedFetch = useCallback<typeof fetch>(async (
    input: RequestInfo | URL,
    init?: RequestInit,
  ) => {
    assertCurrentBinding();
    const fetchImpl = apiOptions?.fetchImpl ?? globalThis.fetch;
    if (!fetchImpl) throw new Error('Authenticated requests require fetch support.');
    const headers = new Headers(init?.headers ?? (input instanceof Request ? input.headers : undefined));
    const activeToken = accountsEnabled && accountModeReady.current ? tokenRef.current : null;
    const accountApiBaseUrl = resolveAccountApiBaseUrl(apiOptions?.baseUrl);
    const attachedAccountBearer = Boolean(
      activeToken && mayAttachAccountBearer(input, accountApiBaseUrl),
    );
    if (attachedAccountBearer) {
      headers.set('Authorization', `Bearer ${activeToken}`);
    } else {
      // Strip even a stale inherited Authorization header on untrusted origins.
      headers.delete('Authorization');
    }
    const response = await fetchImpl(input, {
      ...init,
      headers,
      cache: 'no-store',
      credentials: 'omit',
      redirect: 'error',
      referrerPolicy: 'no-referrer',
    });
    assertCurrentBinding();
    if (attachedAccountBearer && tokenRef.current === activeToken) {
      if (response.status === 401) clearSession();
      if (response.status === 429) {
        setQuotaWarning('Account limit reached. Your identity and session are unchanged. Wait for the limit to reset or contact the platform operator.');
      }
    }
    return response;
  }, [accountsEnabled, apiOptions?.baseUrl, apiOptions?.fetchImpl, assertCurrentBinding, clearSession]);

  const value = useMemo<AccountAuthContextValue>(() => ({
    accountsEnabled,
    token,
    claims,
    isAuthenticated: claims !== null,
    credentialHandoff,
    logoutWarning,
    cancelPendingAuth,
    login,
    redeemInvite,
    logout,
    rotateCredential,
    clearCredentialHandoff: () => setCredentialHandoff(null),
    clearLogoutWarning: () => setLogoutWarning(null),
    authenticatedFetch,
  }), [
    accountsEnabled,
    cancelPendingAuth,
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

  if (capabilityState.status === 'loading' || (capabilityState.status === 'ready' && !verifiedBinding)) {
    return (
      <div
        role="status"
        aria-live="polite"
        data-account-capability-state="loading"
      >
        Verifying customer account mode...
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

  return <AccountAuthContext.Provider value={value}>
    {quotaWarning ? <div role="alert">{quotaWarning} <button type="button" onClick={() => setQuotaWarning(null)}>Dismiss limit notice</button></div> : null}
    {children}
  </AccountAuthContext.Provider>;
}

export function useAccountAuth(): AccountAuthContextValue {
  return useContext(AccountAuthContext);
}

export default AccountAuthProvider;
