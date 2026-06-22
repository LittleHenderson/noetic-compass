import { describe, it, expect } from 'vitest';
import { deriveTraces } from './forexSelectors';
import {
  paperProofFixture,
  uiReadinessFixture,
  dailyScheduleFixture,
  paperDecisionFixture,
  paperRiskFixture,
  dailyBundleFixture,
} from './fixtures';
import type { ForexProofBundle } from './types';

const bundle: ForexProofBundle = {
  paperProof: paperProofFixture,
  uiReadiness: uiReadinessFixture,
  schedule: dailyScheduleFixture,
  decision: paperDecisionFixture,
  risk: paperRiskFixture,
  bundle: dailyBundleFixture,
  fromFixtures: true,
};

describe('deriveTraces', () => {
  const traces = deriveTraces(bundle);

  it('produces one trace per routed paper candidate (US30, NAS100)', () => {
    expect(traces.map((t) => t.symbol).sort()).toEqual(['NAS100', 'US30']);
  });

  it('every trace ends SUPPRESSED with no broker order', () => {
    for (const t of traces) {
      expect(t.packet_status).toBe('SUPPRESSED');
      expect(t.broker_order_placed).toBe(false);
    }
  });

  it('joins real risk sizing onto the matching proposal', () => {
    const us30 = traces.find((t) => t.symbol === 'US30');
    expect(us30?.sized_lots).toBe(0.01);
    expect(us30?.planned_risk_usd).toBe(12.6);
  });

  it('marks the macro gate PASS and the CAS compiler + market gates NOT_RUN', () => {
    const t = traces[0];
    const macro = t.stages.find((s) => s.key === 'gate2_macro');
    const compiler = t.stages.find((s) => s.key === 'gate0_compiler');
    const market = t.stages.find((s) => s.key === 'gate3_market');
    expect(macro?.status).toBe('PASS');
    expect(macro?.exercised).toBe(true);
    expect(compiler?.status).toBe('NOT_RUN');
    expect(compiler?.exercised).toBe(false);
    expect(market?.exercised).toBe(false);
  });

  it('marks the live lock controller CLEAR on day-1 evidence', () => {
    const lock = traces[0].stages.find((s) => s.key === 'live_lock');
    expect(lock?.status).toBe('CLEAR');
  });
});
