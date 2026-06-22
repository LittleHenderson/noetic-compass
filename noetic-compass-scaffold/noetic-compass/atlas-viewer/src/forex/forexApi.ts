// CAS Forex API layer — live read-only backend with bundled-fixture fallback.
//
// The /api/forex/* FastAPI boundary (api/routes/forex_proof.py) serves the real
// paper-proof evidence read-only. In dev/prod these wrappers attempt that
// backend and transparently fall back to the bundled day-1 fixtures on any
// error, so the cockpit never blanks out — it only ever loses freshness, never
// truthfulness. Under vitest we stay on fixtures so unit tests are deterministic
// and never depend on a running server. Force fixtures anywhere with
// VITE_FOREX_API=0.
//
// Every endpoint here is READ-ONLY. There is no order/transfer/unlock path.
// Live trading, broker ACCEPT, and payment transfers remain NOT LICENSED.

import {
  paperProofFixture,
  uiReadinessFixture,
  dailyScheduleFixture,
  paperDecisionFixture,
  paperRiskFixture,
  dailyBundleFixture,
} from './fixtures';
import type {
  ForexProofBundle,
  PaperProofStatus,
  UiReadinessStatus,
  DailyScheduleStatus,
  PaperDecisionStatus,
  PaperRiskStatus,
  DailyBundleStatus,
} from './types';

/**
 * Whether to attempt the live read-only backend. ON in dev/prod (with fixture
 * fallback), OFF under vitest (MODE === 'test') for deterministic tests, and
 * force-OFF anywhere with VITE_FOREX_API=0 / 'false'.
 */
const FOREX_API_DISABLED =
  import.meta.env?.MODE === 'test' ||
  import.meta.env?.VITE_FOREX_API === '0' ||
  import.meta.env?.VITE_FOREX_API === 'false';

export const FOREX_API_ENABLED = !FOREX_API_DISABLED;

const FOREX_API_BASE = '/api/forex';

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${FOREX_API_BASE}${path}`, {
    method: 'GET',
    headers: { Accept: 'application/json' },
  });
  if (!response.ok) {
    throw new Error(`Forex API ${path} failed (${response.status})`);
  }
  return (await response.json()) as T;
}

/**
 * Resolve a value from the live backend when enabled, otherwise the fixture.
 * Any backend error transparently falls back to the fixture so the read-only
 * cockpit never blanks out — it only ever loses freshness, never truthfulness.
 */
async function resolve<T>(path: string, fixture: T): Promise<{ value: T; live: boolean }> {
  if (!FOREX_API_ENABLED) {
    return { value: fixture, live: false };
  }
  try {
    return { value: await getJson<T>(path), live: true };
  } catch {
    return { value: fixture, live: false };
  }
}

export async function fetchPaperProofStatus(): Promise<PaperProofStatus> {
  return (await resolve('/proof/paper', paperProofFixture)).value;
}

export async function fetchUiReadinessStatus(): Promise<UiReadinessStatus> {
  return (await resolve('/proof/ui-readiness', uiReadinessFixture)).value;
}

export async function fetchDailyScheduleStatus(): Promise<DailyScheduleStatus> {
  return (await resolve('/proof/schedule', dailyScheduleFixture)).value;
}

export async function fetchPaperDecisionStatus(): Promise<PaperDecisionStatus> {
  return (await resolve('/proof/decision', paperDecisionFixture)).value;
}

export async function fetchPaperRiskStatus(): Promise<PaperRiskStatus> {
  return (await resolve('/proof/risk', paperRiskFixture)).value;
}

export async function fetchDailyBundleStatus(): Promise<DailyBundleStatus> {
  return (await resolve('/proof/bundle', dailyBundleFixture)).value;
}

/** One read for the whole proof cockpit. */
export async function fetchForexProofBundle(): Promise<ForexProofBundle> {
  const [paperProof, uiReadiness, schedule, decision, risk, bundle] = await Promise.all([
    resolve('/proof/paper', paperProofFixture),
    resolve('/proof/ui-readiness', uiReadinessFixture),
    resolve('/proof/schedule', dailyScheduleFixture),
    resolve('/proof/decision', paperDecisionFixture),
    resolve('/proof/risk', paperRiskFixture),
    resolve('/proof/bundle', dailyBundleFixture),
  ]);

  const anyLive =
    paperProof.live ||
    uiReadiness.live ||
    schedule.live ||
    decision.live ||
    risk.live ||
    bundle.live;

  return {
    paperProof: paperProof.value,
    uiReadiness: uiReadiness.value,
    schedule: schedule.value,
    decision: decision.value,
    risk: risk.value,
    bundle: bundle.value,
    fromFixtures: !anyLive,
  };
}
