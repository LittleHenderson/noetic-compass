export const API_BASE_STORAGE_KEY = "cas_forex_api_base";
export const OWNER_TOKEN_STORAGE_KEY = "cas_forex_owner_token";
const LAST_SUCCESSFUL_API_BASE_STORAGE_KEY = "cas_forex_last_successful_api_base";
const FAILED_API_BASE_COOLDOWN_MS = 15_000;

// Owner pairing token. On the owner's own PC (loopback) the API needs no token;
// this is for reaching the cockpit from ANOTHER device (phone) once LAN mode is
// on. When set, it rides every request as X-CAS-Owner-Token. Stored locally.
export function getOwnerToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(OWNER_TOKEN_STORAGE_KEY);
  } catch {
    return null;
  }
}

export function setOwnerToken(token: string | null): void {
  if (typeof window === "undefined") return;
  try {
    const cleaned = (token || "").trim();
    if (cleaned) window.localStorage.setItem(OWNER_TOKEN_STORAGE_KEY, cleaned);
    else window.localStorage.removeItem(OWNER_TOKEN_STORAGE_KEY);
  } catch {
    // Private mode / storage disabled — nothing to persist.
  }
}

function authHeaders(extra?: Record<string, string>): Record<string, string> {
  const headers: Record<string, string> = { ...(extra || {}) };
  const token = getOwnerToken();
  if (token) headers["X-CAS-Owner-Token"] = token;
  return headers;
}
const DEFAULT_API_BASE =
  import.meta.env.VITE_CAS_FOREX_API_BASE ?? "http://127.0.0.1:8765/api/forex";
let lastSuccessfulApiBase: string | null = null;
const failedApiBaseUntil = new Map<string, number>();

export function getApiBase(): string {
  if (typeof window === "undefined") return DEFAULT_API_BASE;
  return window.localStorage.getItem(API_BASE_STORAGE_KEY) || DEFAULT_API_BASE;
}

export function setApiBase(value: string): void {
  if (typeof window === "undefined") return;
  const cleaned = value.trim().replace(/\/+$/, "");
  clearRememberedApiBase();
  if (!cleaned) {
    window.localStorage.removeItem(API_BASE_STORAGE_KEY);
    return;
  }
  window.localStorage.setItem(API_BASE_STORAGE_KEY, cleaned);
}

export function resetApiBase(): void {
  if (typeof window === "undefined") return;
  clearRememberedApiBase();
  window.localStorage.removeItem(API_BASE_STORAGE_KEY);
}

function normalizeApiBase(value: string): string {
  return value.trim().replace(/\/+$/, "");
}

function readLastSuccessfulApiBase(): string | null {
  if (lastSuccessfulApiBase) return lastSuccessfulApiBase;
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(LAST_SUCCESSFUL_API_BASE_STORAGE_KEY);
  } catch {
    return null;
  }
}

function rememberSuccessfulApiBase(base: string): void {
  lastSuccessfulApiBase = normalizeApiBase(base);
  failedApiBaseUntil.delete(lastSuccessfulApiBase);
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(LAST_SUCCESSFUL_API_BASE_STORAGE_KEY, lastSuccessfulApiBase);
  } catch {
    // Browser storage can be unavailable in private mode; in-memory stickiness still helps this session.
  }
}

function clearRememberedApiBase(): void {
  lastSuccessfulApiBase = null;
  if (typeof window === "undefined") return;
  try {
    window.localStorage.removeItem(LAST_SUCCESSFUL_API_BASE_STORAGE_KEY);
  } catch {
    // Browser storage can be unavailable in private mode; clearing in-memory state is still enough.
  }
}

function rememberFailedApiBase(base: string, error?: unknown): void {
  if (!shouldCooldownApiBase(error)) return;
  failedApiBaseUntil.set(normalizeApiBase(base), Date.now() + FAILED_API_BASE_COOLDOWN_MS);
}

function shouldCooldownApiBase(error: unknown): boolean {
  if (!error) return true;
  if (error instanceof TypeError) return true;
  if (error instanceof Error && error.message.startsWith("API 404:")) return true;
  if (typeof DOMException !== "undefined" && error instanceof DOMException) {
    return error.name === "AbortError" || error.name === "TimeoutError";
  }
  return false;
}

function isApiBaseCoolingDown(base: string): boolean {
  const normalized = normalizeApiBase(base);
  const until = failedApiBaseUntil.get(normalized);
  if (!until) return false;
  if (Date.now() < until) return true;
  failedApiBaseUntil.delete(normalized);
  return false;
}

function availableApiBases(bases: Array<string | null | undefined>): string[] {
  const normalized = Array.from(new Set(bases.map((base) => base ? normalizeApiBase(base) : "").filter(Boolean)));
  const active = normalized.filter((base) => !isApiBaseCoolingDown(base));
  return active.length ? active : normalized;
}

function apiGetBases(): string[] {
  const savedBase = getApiBase();
  const rememberedBase = readLastSuccessfulApiBase();
  const isLocalBrowser = typeof window === "undefined"
    || ["127.0.0.1", "localhost", "::1"].includes(window.location.hostname);
  const bases = isLocalBrowser
    ? [rememberedBase, savedBase, DEFAULT_API_BASE]
    : [savedBase, rememberedBase, DEFAULT_API_BASE];
  if (typeof window !== "undefined") {
    bases.push(`${window.location.origin}/api/forex`);
  }
  return availableApiBases(bases);
}

function apiMutationBases(): string[] {
  const rememberedBase = readLastSuccessfulApiBase();
  const bases = rememberedBase ? [rememberedBase, ...apiGetBases()] : apiGetBases();
  return availableApiBases(bases);
}

export async function apiGet<T>(path: string, timeoutMs = 8000): Promise<T> {
  let lastError: unknown = null;
  for (const base of apiGetBases()) {
    try {
      const res = await fetch(`${base}${path}`, {
        headers: authHeaders(),
        signal: AbortSignal.timeout(timeoutMs),
      });
      if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`);
      rememberSuccessfulApiBase(base);
      return await res.json();
    } catch (err) {
      rememberFailedApiBase(base, err);
      lastError = err;
    }
  }
  throw lastError instanceof Error ? lastError : new Error("API request failed");
}

export async function apiPost<T>(path: string): Promise<T> {
  let lastError: unknown = null;
  for (const base of apiMutationBases()) {
    try {
      const res = await fetch(`${base}${path}`, {
        method: "POST",
        headers: authHeaders({ "Content-Type": "application/json" }),
        signal: AbortSignal.timeout(8000),
      });
      if (!res.ok) {
        const err = new Error(`API ${res.status}: ${res.statusText}`);
        if (res.status !== 404) throw err;
        rememberFailedApiBase(base, err);
        lastError = err;
        continue;
      }
      rememberSuccessfulApiBase(base);
      return res.json();
    } catch (err) {
      rememberFailedApiBase(base, err);
      lastError = err;
    }
  }
  throw lastError instanceof Error ? lastError : new Error("API request failed");
}

export async function apiPostJson<TResp, TBody>(
  path: string,
  body: TBody,
  timeoutMs = 10_000,
): Promise<TResp> {
  let lastError: unknown = null;
  for (const base of apiMutationBases()) {
    try {
      const res = await fetch(`${base}${path}`, {
        method: "POST",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify(body),
        signal: AbortSignal.timeout(timeoutMs),
      });
      const text = await res.text();
      let parsed: unknown;
      try {
        parsed = text ? JSON.parse(text) : null;
      } catch {
        parsed = text;
      }
      if (!res.ok) {
        const err = new Error(`API ${res.status}: ${res.statusText}`) as Error & {
          status?: number;
          payload?: unknown;
        };
        err.status = res.status;
        err.payload = parsed;
        if (res.status !== 404) throw err;
        rememberFailedApiBase(base, err);
        lastError = err;
        continue;
      }
      rememberSuccessfulApiBase(base);
      return parsed as TResp;
    } catch (err) {
      rememberFailedApiBase(base, err);
      lastError = err;
    }
  }
  throw lastError instanceof Error ? lastError : new Error("API request failed");
}

export async function apiDelete<T>(path: string): Promise<T> {
  let lastError: unknown = null;
  for (const base of apiMutationBases()) {
    try {
      const res = await fetch(`${base}${path}`, {
        method: "DELETE",
        headers: authHeaders({ "Content-Type": "application/json" }),
        signal: AbortSignal.timeout(8000),
      });
      if (!res.ok) {
        const err = new Error(`API ${res.status}: ${res.statusText}`);
        if (res.status !== 404) throw err;
        rememberFailedApiBase(base, err);
        lastError = err;
        continue;
      }
      rememberSuccessfulApiBase(base);
      return res.json();
    } catch (err) {
      rememberFailedApiBase(base, err);
      lastError = err;
    }
  }
  throw lastError instanceof Error ? lastError : new Error("API request failed");
}
