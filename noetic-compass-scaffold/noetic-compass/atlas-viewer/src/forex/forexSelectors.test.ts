import { describe, it, expect } from 'vitest';
import { deriveBannerState, deriveLiveEligibility } from './forexSelectors';
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

describe('deriveBannerState', () => {
  const s = deriveBannerState(bundle);

  it('never asserts a live state on day-1 evidence', () => {
    expect(s.liveMode).toBe(false);
    expect(s.paperTrading).toBe(true);
    expect(s.mode).toBe('PAPER_MT5');
  });

  it('keeps the three hard boundaries NOT LICENSED', () => {
    expect(s.deploymentStatus).toBe('NOT LICENSED');
    expect(s.brokerAcceptStatus).toBe('NOT LICENSED');
    expect(s.paymentTransferStatus).toBe('NOT LICENSED');
  });

  it('reports proof progress and verified chain', () => {
    expect(s.paperProof).toEqual({ completed: 1, required: 30 });
    expect(s.multiDayMaturity).toEqual({ complete: 1, required: 5, ready: false });
    expect(s.evidenceChainVerified).toBe(true);
    expect(s.liveLockActive).toBe(false);
  });
});

describe('deriveLiveEligibility', () => {
  const rows = deriveLiveEligibility(bundle);

  it('marks the 30-day paper gate partial at 1/30', () => {
    const paper = rows.find((r) => r.key === 'paper_30d');
    expect(paper?.state).toBe('PARTIAL');
    expect(paper?.detail).toContain('1 / 30');
  });

  it('marks no live lock as MET and WORM as UNAVAILABLE', () => {
    expect(rows.find((r) => r.key === 'no_live_lock')?.state).toBe('MET');
    expect(rows.find((r) => r.key === 'worm')?.state).toBe('UNAVAILABLE');
  });

  it('keeps the 12-month backtest edge OPEN', () => {
    expect(rows.find((r) => r.key === 'backtest_12m')?.state).toBe('OPEN');
  });
});
