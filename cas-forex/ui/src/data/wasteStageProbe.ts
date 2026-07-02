const DEFAULT_API_BASE =
  import.meta.env.VITE_CAS_FOREX_API_BASE ?? "http://127.0.0.1:8765/api/forex";
const API_BASE_STORAGE_KEY = "cas_forex_api_base";
const LAST_SUCCESSFUL_API_BASE_STORAGE_KEY = "cas_forex_last_successful_api_base";
const FAILED_STAGE_API_BASE_COOLDOWN_MS = 15_000;
const DEFAULT_STAGE_PROBE_TIMEOUT_MS = 1_500;
const DEFAULT_STAGE_PROBE_MAX_AGE_MS = 1_000;

interface CachedWasteStage {
  savedAt: number;
  payload: Record<string, unknown>;
}

interface WasteLoopProbeOptions {
  timeoutMs?: number;
  maxAgeMs?: number;
  force?: boolean;
}

interface WasteLoopFromStageOptions {
  reportKind: string;
  claimBoundary: string;
}

let cachedWasteStage: CachedWasteStage | null = null;
let inflightWasteStage: Promise<Record<string, unknown> | null> | null = null;
let lastSuccessfulWasteStageApiBase: string | null = null;
const failedWasteStageApiBaseUntil = new Map<string, number>();

export async function fetchWasteStageProbe(
  options: WasteLoopProbeOptions = {},
): Promise<Record<string, unknown> | null> {
  const maxAgeMs = options.maxAgeMs ?? DEFAULT_STAGE_PROBE_MAX_AGE_MS;
  if (!options.force && cachedWasteStage && Date.now() - cachedWasteStage.savedAt <= maxAgeMs) {
    return { ...cachedWasteStage.payload };
  }
  if (!options.force && inflightWasteStage) {
    const payload = await inflightWasteStage;
    return payload ? { ...payload } : null;
  }

  inflightWasteStage = fetchWasteStageFromBases(options.timeoutMs ?? DEFAULT_STAGE_PROBE_TIMEOUT_MS)
    .then((payload) => {
      if (payload) {
        cachedWasteStage = {
          savedAt: Date.now(),
          payload: { ...payload },
        };
      }
      return payload;
    })
    .finally(() => {
      inflightWasteStage = null;
    });

  const payload = await inflightWasteStage;
  return payload ? { ...payload } : null;
}

export function wasteLoopFromStagePayload(
  payload: Record<string, unknown>,
  options: WasteLoopFromStageOptions,
): Record<string, unknown> {
  const running = Boolean(payload.running);
  const stage = stringValue(payload.stage) || stringValue(payload.current_stage) || "idle";
  return {
    ...payload,
    report_kind: options.reportKind,
    running,
    status: running ? "RUNNING" : "OFFLINE",
    current_stage: stage,
    stage,
    mode: payload.mode ?? "PAPER",
    last_reason: payload.detail ?? null,
    last_run_iso: payload.updated_at ?? null,
    claim_boundary: options.claimBoundary,
  };
}

async function fetchWasteStageFromBases(timeoutMs: number): Promise<Record<string, unknown> | null> {
  for (const base of wasteStageApiBases()) {
    try {
      const res = await fetch(`${base}/waste-loop/stage`, {
        signal: AbortSignal.timeout(timeoutMs),
      });
      if (!res.ok) {
        rememberFailedWasteStageApiBase(base, new Error(`API ${res.status}: ${res.statusText}`));
        continue;
      }
      const payload: unknown = await res.json();
      if (payload && typeof payload === "object") {
        rememberSuccessfulWasteStageApiBase(base);
        return payload as Record<string, unknown>;
      }
    } catch (error) {
      rememberFailedWasteStageApiBase(base, error);
      // Try the next configured base. The caller decides whether null is useful.
    }
  }
  return null;
}

function wasteStageApiBases(): string[] {
  const savedBase = readSavedApiBase();
  const rememberedBase = readLastSuccessfulWasteStageApiBase();
  const isLocalBrowser = typeof window === "undefined"
    || ["127.0.0.1", "localhost", "::1"].includes(window.location.hostname);
  const bases = isLocalBrowser
    ? [rememberedBase, savedBase, DEFAULT_API_BASE]
    : [savedBase, rememberedBase, DEFAULT_API_BASE];
  if (typeof window !== "undefined") {
    bases.push(`${window.location.origin}/api/forex`);
  }
  return availableWasteStageApiBases(bases);
}

function readSavedApiBase(): string {
  if (typeof window === "undefined") return DEFAULT_API_BASE;
  try {
    return window.localStorage.getItem(API_BASE_STORAGE_KEY) || DEFAULT_API_BASE;
  } catch {
    return DEFAULT_API_BASE;
  }
}

function readLastSuccessfulWasteStageApiBase(): string | null {
  if (lastSuccessfulWasteStageApiBase) return lastSuccessfulWasteStageApiBase;
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(LAST_SUCCESSFUL_API_BASE_STORAGE_KEY);
  } catch {
    return null;
  }
}

function rememberSuccessfulWasteStageApiBase(base: string): void {
  lastSuccessfulWasteStageApiBase = normalizeApiBase(base);
  failedWasteStageApiBaseUntil.delete(lastSuccessfulWasteStageApiBase);
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(LAST_SUCCESSFUL_API_BASE_STORAGE_KEY, lastSuccessfulWasteStageApiBase);
  } catch {
    // Browser storage can be unavailable in private mode; in-memory stickiness still helps this session.
  }
}

function rememberFailedWasteStageApiBase(base: string, error?: unknown): void {
  if (!shouldCooldownWasteStageApiBase(error)) return;
  failedWasteStageApiBaseUntil.set(
    normalizeApiBase(base),
    Date.now() + FAILED_STAGE_API_BASE_COOLDOWN_MS,
  );
}

function shouldCooldownWasteStageApiBase(error: unknown): boolean {
  if (!error) return true;
  if (error instanceof TypeError) return true;
  if (error instanceof Error && error.message.startsWith("API 404:")) return true;
  if (typeof DOMException !== "undefined" && error instanceof DOMException) {
    return error.name === "AbortError" || error.name === "TimeoutError";
  }
  return false;
}

function isWasteStageApiBaseCoolingDown(base: string): boolean {
  const normalized = normalizeApiBase(base);
  const until = failedWasteStageApiBaseUntil.get(normalized);
  if (!until) return false;
  if (Date.now() < until) return true;
  failedWasteStageApiBaseUntil.delete(normalized);
  return false;
}

function availableWasteStageApiBases(bases: Array<string | null | undefined>): string[] {
  const normalized = Array.from(new Set(bases.map((base) => base ? normalizeApiBase(base) : "").filter(Boolean)));
  const active = normalized.filter((base) => !isWasteStageApiBaseCoolingDown(base));
  return active.length ? active : normalized;
}

function normalizeApiBase(value: string): string {
  return value.trim().replace(/\/+$/, "");
}

function stringValue(value: unknown): string {
  return typeof value === "string" ? value : "";
}
