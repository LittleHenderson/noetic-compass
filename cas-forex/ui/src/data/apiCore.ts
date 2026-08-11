export const API_BASE_STORAGE_KEY = "cas_forex_api_base";
export const OWNER_TOKEN_STORAGE_KEY = "cas_forex_owner_token";
export const OWNER_TOKEN_HASH_KEY = "cas_owner_token";
export const API_BASE_HASH_KEY = "cas_api_base";
const LAST_SUCCESSFUL_API_BASE_STORAGE_KEY = "cas_forex_last_successful_api_base";
const FAILED_API_BASE_COOLDOWN_MS = 15_000;

export interface OwnerPairingConsumption {
  consumed: boolean;
  page: string | null;
}

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

export function consumeOwnerTokenFromLocation(): boolean {
  if (typeof window === "undefined") return false;
  return consumeOwnerPairingFromUrl(window.location.href, { scrubCurrentLocation: true }).consumed;
}

function isTrustedPairingApiBase(value: string): boolean {
  let parsed: URL;
  try {
    parsed = new URL(value.trim());
  } catch {
    return false;
  }
  if (!["http:", "https:"].includes(parsed.protocol)) return false;
  if (parsed.username || parsed.password || parsed.search || parsed.hash) return false;
  if (parsed.pathname.replace(/\/+$/, "") !== "/api/forex") return false;
  return isTrustedPairingHost(parsed.hostname);
}

function isTrustedPairingHost(hostname: string): boolean {
  const host = hostname.trim().replace(/^\[|\]$/g, "").toLowerCase();
  if (["localhost", "127.0.0.1", "::1"].includes(host)) return true;
  if (host.endsWith(".local")) return true;
  if (isPrivateIpv4Host(host)) return true;
  if (typeof window === "undefined") return false;
  const currentHost = window.location.hostname.trim().replace(/^\[|\]$/g, "").toLowerCase();
  return Boolean(currentHost && host === currentHost);
}

function isPrivateIpv4Host(host: string): boolean {
  const parts = host.split(".").map((part) => Number(part));
  if (parts.length !== 4 || parts.some((part) => !Number.isInteger(part) || part < 0 || part > 255)) {
    return false;
  }
  const [a, b] = parts;
  return a === 10
    || a === 127
    || (a === 172 && b >= 16 && b <= 31)
    || (a === 192 && b === 168)
    || (a === 169 && b === 254);
}

export function consumeOwnerPairingFromUrl(
  rawUrl: string,
  options: { scrubCurrentLocation?: boolean } = {},
): OwnerPairingConsumption {
  if (typeof window === "undefined") return { consumed: false, page: null };
  let parsed: URL;
  try {
    parsed = new URL(rawUrl, window.location.href);
  } catch {
    return { consumed: false, page: null };
  }
  const hash = parsed.hash.startsWith("#")
    ? parsed.hash.slice(1)
    : parsed.hash;
  const hashParams = new URLSearchParams(hash);
  const token = hashParams.get(OWNER_TOKEN_HASH_KEY) ?? parsed.searchParams.get(OWNER_TOKEN_HASH_KEY);
  const apiBase = hashParams.get(API_BASE_HASH_KEY) ?? parsed.searchParams.get(API_BASE_HASH_KEY);
  const page = hashParams.get("page") ?? parsed.searchParams.get("page");
  if (!token && !apiBase) return { consumed: false, page };

  if (token) {
    setOwnerToken(token);
  }
  if (apiBase && isTrustedPairingApiBase(apiBase)) {
    setApiBase(apiBase);
  }
  if (options.scrubCurrentLocation) {
    scrubPairingStateFromCurrentLocation();
  }
  return { consumed: true, page };
}

function scrubPairingStateFromCurrentLocation(): void {
  const next = new URL(window.location.href);
  next.searchParams.delete(OWNER_TOKEN_HASH_KEY);
  next.searchParams.delete(API_BASE_HASH_KEY);
  const currentHash = window.location.hash.startsWith("#")
    ? window.location.hash.slice(1)
    : window.location.hash;
  const params = new URLSearchParams(currentHash);
  params.delete(OWNER_TOKEN_HASH_KEY);
  params.delete(API_BASE_HASH_KEY);
  const remainingHash = params.toString();
  next.hash = remainingHash ? `#${remainingHash}` : "";
  window.history.replaceState(null, "", next.toString());
}

function authHeaders(extra?: Record<string, string>, apiBase?: string): Record<string, string> {
  const headers: Record<string, string> = { ...(extra || {}) };
  const token = getOwnerToken();
  if (token) headers["X-CAS-Owner-Token"] = token;
  if (apiBase) headers["X-CAS-Client-API-Base"] = normalizeApiBase(apiBase);
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

function readSavedApiBaseOverride(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(API_BASE_STORAGE_KEY);
  } catch {
    return null;
  }
}

function sameOriginApiBase(): string | null {
  if (typeof window === "undefined") return null;
  if (isCapacitorShell()) return null;
  return `${window.location.origin}/api/forex`;
}

function isCapacitorShell(): boolean {
  if (typeof window === "undefined") return false;
  const maybeCapacitor = (window as unknown as { Capacitor?: unknown }).Capacitor;
  return Boolean(maybeCapacitor) || window.location.protocol === "capacitor:";
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
  const savedOverride = readSavedApiBaseOverride();
  const rememberedBase = readLastSuccessfulApiBase();
  const originBase = sameOriginApiBase();
  const isCapacitor = isCapacitorShell();
  const isLocalBrowser = !isCapacitor && (
    typeof window === "undefined"
    || ["127.0.0.1", "localhost", "::1"].includes(window.location.hostname)
  );
  const bases = isLocalBrowser
    ? [savedOverride, originBase, rememberedBase, DEFAULT_API_BASE]
    : [savedOverride, rememberedBase, originBase, DEFAULT_API_BASE];
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
        headers: authHeaders(undefined, base),
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

export interface ApiBlobDownload {
  blob: Blob;
  filename: string | null;
}

export async function apiDownloadBlob(path: string, timeoutMs = 30_000): Promise<ApiBlobDownload> {
  let lastError: unknown = null;
  for (const base of apiMutationBases()) {
    try {
      const res = await fetch(`${base}${path}`, {
        headers: authHeaders(undefined, base),
        signal: AbortSignal.timeout(timeoutMs),
      });
      if (!res.ok) {
        const err = new Error(`API ${res.status}: ${res.statusText}`);
        if (res.status !== 404) throw err;
        rememberFailedApiBase(base, err);
        lastError = err;
        continue;
      }
      rememberSuccessfulApiBase(base);
      return {
        blob: await res.blob(),
        filename: parseContentDispositionFilename(res.headers.get("content-disposition")),
      };
    } catch (err) {
      rememberFailedApiBase(base, err);
      lastError = err;
    }
  }
  throw lastError instanceof Error ? lastError : new Error("API download failed");
}

function parseContentDispositionFilename(value: string | null): string | null {
  if (!value) return null;
  const utf8Match = value.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8Match?.[1]) {
    try {
      return decodeURIComponent(utf8Match[1].trim().replace(/^"|"$/g, ""));
    } catch {
      return utf8Match[1].trim().replace(/^"|"$/g, "") || null;
    }
  }
  const match = value.match(/filename=([^;]+)/i);
  return match?.[1]?.trim().replace(/^"|"$/g, "") || null;
}

export async function apiPost<T>(path: string): Promise<T> {
  let lastError: unknown = null;
  for (const base of apiMutationBases()) {
    try {
      const res = await fetch(`${base}${path}`, {
        method: "POST",
        headers: authHeaders({ "Content-Type": "application/json" }, base),
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
        headers: authHeaders({ "Content-Type": "application/json" }, base),
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
        headers: authHeaders({ "Content-Type": "application/json" }, base),
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
