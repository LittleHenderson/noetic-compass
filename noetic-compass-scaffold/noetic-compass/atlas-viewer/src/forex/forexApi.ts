// CAS Forex API layer — Phase 0 "fixture mode" with a backend-ready fetch path.
//
// There is no /api/forex/* backend yet. Until one lands, FOREX_API_ENABLED is
// false and every read resolves from bundled day-1 fixtures (truthful real
// evidence, served statically). When the FastAPI boundary from the UI/UX plan
// is wired, flip the flag (or set VITE_FOREX_API=1) and the same wrappers fetch
// the live read-only status without any component change.
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

/** Backend feature flag. Default OFF — no forex API exists yet. */
export const FOREX_API_ENABLED =
  import.meta.env?.VITE_FOREX_API === '1' ||
  import.meta.env?.VITE_FOREX_API === 'true';

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
