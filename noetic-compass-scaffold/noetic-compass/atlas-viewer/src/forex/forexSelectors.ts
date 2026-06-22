// Pure selectors that derive cockpit display state from the loaded evidence
// bundle. No fetching, no side effects — easy to unit-test and reuse.

import type {
  ForexBannerState,
  ForexBrokerMode,
  ForexEvidenceHash,
  ForexProofBundle,
  ForexTrace,
  PipelineStage,
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

/**
 * Derive audit traces from the real day-1 evidence: one trace per paper route
 * candidate, joining the route decision, risk sizing, and proof receipt.
 *
 * Truthfulness rule: the day-1 PAPER-ROUTE loop is the decision + risk + receipt
 * tracks, not the full backtest/auditor pipeline. Stages the paper loop did not
 * exercise (CAS compiler, market gate) are marked NOT_RUN with an honest detail
 * instead of a fabricated PASS.
 */
export function deriveTraces(bundle: ForexProofBundle): ForexTrace[] {
  const decision = bundle.decision.latest_decision;
  const review = bundle.risk.latest_review;
  const report = bundle.paperProof.report;
  const summary = report.daily_summaries[report.daily_summaries.length - 1];
  const liveLocked = report.live_locks.length > 0;

  return decision.symbol_decisions.map((sd) => {
    const sizing = review.sizing.find((s) => s.proposal_id === sd.proposal.proposal_id) ?? null;

    const stages: PipelineStage[] = [
      {
        key: 'forecast',
        label: 'Forecast Harness',
        status: 'ROUTED',
        exercised: true,
        detail: `${sd.proposal.model_version} · ${sd.direction} · confidence ${sd.confidence.toFixed(4)}`,
      },
      {
        key: 'gate0_compiler',
        label: 'Gate 0 · CAS Compiler',
        status: 'NOT_RUN',
        exercised: false,
        detail: 'Full CAS compiler/admissibility gate runs in the backtest/auditor path, not the day-1 paper-route loop.',
      },
      {
        key: 'gate1_risk',
        label: 'Gate 1 · Risk',
        status: sizing ? 'ALLOWED' : 'NOT_RUN',
        exercised: !!sizing,
        detail: sizing
          ? `Sized ${sizing.sized_lots} lots · planned risk $${sizing.planned_risk_usd} of $${sizing.max_risk_usd} cap · ${sizing.attempt_status}`
          : 'No sizing recorded for this candidate.',
      },
      {
        key: 'gate2_macro',
        label: 'Gate 2 · Macro',
        status: 'PASS',
        exercised: true,
        detail: `${decision.macro_status} · ${decision.macro_reason} · event context: ${decision.event_context}`,
      },
      {
        key: 'gate3_market',
        label: 'Gate 3 · Market',
        status: 'NOT_RUN',
        exercised: false,
        detail: 'Market gate not exercised in the day-1 paper-route loop.',
      },
      {
        key: 'gate4_execution',
        label: 'Gate 4 · Execution',
        status: 'NO_ORDER',
        exercised: true,
        detail: `Orders attempted ${summary?.orders_attempted ?? 0}; no broker order placed (paper-only).`,
      },
      {
        key: 'broker',
        label: 'Broker Outcome',
        status: 'NO_ORDER',
        exercised: true,
        detail: `Orders paper-executed ${summary?.orders_paper_executed ?? 0} on ${summary?.server ?? 'demo source'}.`,
      },
      {
        key: 'post_trade',
        label: 'Post-Trade Harness',
        status: report.open_positions_reconciled ? 'VERIFIED' : 'NOT_RUN',
        exercised: report.open_positions_reconciled,
        detail: report.open_positions_reconciled
          ? 'Open positions reconciled; no new fill to settle.'
          : 'Not run.',
      },
      {
        key: 'evidence',
        label: 'Evidence Store',
        status: 'SUPPRESSED',
        exercised: true,
        detail: 'Paper route candidate recorded and hash-bound; packet status SUPPRESSED (no order).',
      },
      {
        key: 'live_lock',
        label: 'Live Lock Controller',
        status: liveLocked ? 'LIVE_LOCKED' : 'CLEAR',
        exercised: true,
        detail: liveLocked ? `${report.live_locks.length} live lock(s) active.` : 'No live lock active.',
      },
    ];

    const hashes: ForexEvidenceHash[] = summary
      ? [
          {
            label: 'broker receipt sha256',
            hash: summary.broker_receipt_hash_sha256,
            verified: summary.broker_receipt_validated,
          },
          {
            label: 'broker export sha256',
            hash: summary.broker_export_sha256,
            verified: summary.broker_source_verified,
          },
          { label: 'account id hash', hash: summary.account_id_hash },
        ]
      : [];

    return {
      trace_id: sd.proposal.proposal_id,
      symbol: sd.symbol,
      date: decision.date,
      timeframe: sd.proposal.timeframe,
      direction: sd.direction,
      confidence: sd.confidence,
      route_action: sd.action,
      packet_status: 'SUPPRESSED',
      broker_order_placed: false,
      sized_lots: sizing ? sizing.sized_lots : null,
      planned_risk_usd: sizing ? sizing.planned_risk_usd : null,
      stages,
      hashes,
      chain_verified: report.chain_verified,
    };
  });
}
