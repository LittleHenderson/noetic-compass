// Pure selectors that derive cockpit display state from the loaded evidence
// bundle. No fetching, no side effects — easy to unit-test and reuse.

import type {
  ForexBannerState,
  ForexBrokerMode,
  ForexProofBundle,
} from './types';

const KNOWN_MODES: ForexBrokerMode[] = [
  'SIMULATED',
  'PAPER_MT5',
  'PAPER_MT4',
  'LIVE_LOCKED',
  'NOT_LICENSED',
];

function normalizeMode(raw: string | undefined): ForexBrokerMode {
  if (!raw) return 'SIMULATED';
  const upper = raw.toUpperCase();
  return (KNOWN_MODES.find((m) => m === upper) ?? 'SIMULATED') as ForexBrokerMode;
}

/**
 * Derive the always-visible banner state. By construction this can never assert
 * a green LIVE state: liveMode is read straight from evidence (false on day 1)
 * and the mode is clamped to the paper/sim/locked set.
 */
export function deriveBannerState(bundle: ForexProofBundle): ForexBannerState {
  const report = bundle.paperProof.report;
  const latestSummary = report.daily_summaries[report.daily_summaries.length - 1];

  const liveMode = report.live_mode_used || (latestSummary?.live_mode ?? false);
  const mode = liveMode ? 'LIVE_LOCKED' : normalizeMode(latestSummary?.broker_mode);

  return {
    mode,
    paperTrading: true,
    liveMode,
    deploymentStatus: bundle.paperProof.deployment_status,
    brokerAcceptStatus: bundle.paperProof.broker_accept_status,
    paymentTransferStatus: bundle.paperProof.payment_transfer_status,
    evidenceChainVerified:
      report.chain_verified &&
      bundle.uiReadiness.chains_verified.paper_proof &&
      bundle.uiReadiness.chains_verified.paper_decision &&
      bundle.uiReadiness.chains_verified.paper_risk,
    paperProof: {
      completed: report.completed_trading_days,
      required: report.required_trading_days,
    },
    multiDayMaturity: {
      complete: bundle.uiReadiness.complete_bundle_days,
      required: bundle.uiReadiness.min_daily_bundles_for_ui,
      ready: bundle.uiReadiness.readiness_status === 'READY_FOR_UI_UX',
    },
    liveLockActive: report.live_locks.length > 0,
    fromFixtures: bundle.fromFixtures,
  };
}

/** Live-eligibility checklist rows for the proof center. */
export interface EligibilityRow {
  key: string;
  label: string;
  state: 'OPEN' | 'PARTIAL' | 'MET' | 'BLOCKED' | 'UNAVAILABLE';
  detail: string;
}

export function deriveLiveEligibility(bundle: ForexProofBundle): EligibilityRow[] {
  const report = bundle.paperProof.report;
  const r = bundle.uiReadiness;

  return [
    {
      key: 'backtest_12m',
      label: '12-month multi-symbol backtest evidence',
      state: 'OPEN',
      detail: 'Trading edge remains OPEN; broker-grade 12-month proof not yet established.',
    },
    {
      key: 'paper_30d',
      label: '30 real trading days paper evidence',
      state: report.completed_trading_days >= 30 ? 'MET' : 'PARTIAL',
      detail: `${report.completed_trading_days} / ${report.required_trading_days} verified paper days.`,
    },
    {
      key: 'broker_terminal',
      label: 'Broker / demo terminal proof',
      state: r.broker_verified_days > 0 ? 'PARTIAL' : 'OPEN',
      detail: `${r.broker_verified_days} day(s) BROKER_API_VERIFIED on the demo source.`,
    },
    {
      key: 'legal_account',
      label: 'Legal / account acknowledgments',
      state: 'OPEN',
      detail: 'Personal-account acknowledgments not yet captured in the UI.',
    },
    {
      key: 'no_pooled',
      label: 'No pooled / family / friend / client / fee-based capital',
      state: 'OPEN',
      detail: 'Account-type attestation pending in settings.',
    },
    {
      key: 'no_live_lock',
      label: 'No active LIVE_LOCKED',
      state: report.live_locks.length === 0 ? 'MET' : 'BLOCKED',
      detail:
        report.live_locks.length === 0
          ? 'No live lock present.'
          : `${report.live_locks.length} live lock(s) active.`,
    },
    {
      key: 'worm',
      label: 'WORM / Object-Lock evidence anchoring',
      state: 'UNAVAILABLE',
      detail: 'CAS Forex currently has a local hash chain only; WORM is not wired.',
    },
  ];
}
