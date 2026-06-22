// /forex/proof — the CAS Forex Proof Center.
//
// First and default forex screen. Its single job is to show the truthful proof
// state so the UI never emotionally implies "ready to trade": paper/sim only,
// local hash chain only, trading edge OPEN, 1/30 paper days, and every
// live-money / payment control disabled and labeled NOT LICENSED.

import { useEffect, useState, type CSSProperties, type ReactNode } from 'react';
import { motion } from 'framer-motion';
import { COLORS, ACCENT_TEAL, FONT_MONO, SPRING_GENTLE } from '../../lib/designTokens';
import { fetchForexProofBundle } from '../forexApi';
import { deriveLiveEligibility, type EligibilityRow } from '../forexSelectors';
import type { ForexProofBundle } from '../types';
import { ForexModeBanner } from '../components/ForexModeBanner';
import { ForexPanel } from '../components/ForexPanel';
import { ForexStatusChip } from '../components/ForexStatusChip';
import { ClaimStatusChip } from '../components/ClaimStatusChip';
import { EvidenceHashRow } from '../components/EvidenceHashRow';
import { LockReasonList } from '../components/LockReasonList';

// ── small layout helpers ─────────────────────────────────────────────────────

const stackStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 14,
  width: '100%',
};

const defGridStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'minmax(120px, max-content) 1fr',
  rowGap: 8,
  columnGap: 16,
  fontSize: 12.5,
};

const defKeyStyle: CSSProperties = { color: COLORS.textMuted };
const defValStyle: CSSProperties = { color: COLORS.textPrimary, fontWeight: 600 };

function Def({ k, v }: { k: string; v: ReactNode }) {
  return (
    <>
      <span style={defKeyStyle}>{k}</span>
      <span style={defValStyle}>{v}</span>
    </>
  );
}

const monoBlockStyle: CSSProperties = {
  fontFamily: FONT_MONO,
  fontSize: 11.5,
  color: COLORS.textSecondary,
  background: 'rgba(255,255,255,0.03)',
  border: `1px solid ${COLORS.borderSubtle}`,
  borderRadius: 6,
  padding: '10px 12px',
  lineHeight: 1.5,
  wordBreak: 'break-all',
  whiteSpace: 'pre-wrap',
};

// ── eligibility row ──────────────────────────────────────────────────────────

function EligibilityRowView({ row }: { row: EligibilityRow }) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'flex-start',
        justifyContent: 'space-between',
        gap: 12,
        padding: '8px 0',
        borderBottom: `1px solid ${COLORS.borderSubtle}`,
      }}
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
        <span style={{ fontSize: 12.5, color: COLORS.textPrimary, fontWeight: 600 }}>{row.label}</span>
        <span style={{ fontSize: 11.5, color: COLORS.textMuted, lineHeight: 1.4 }}>{row.detail}</span>
      </div>
      <ClaimStatusChip status={row.state} style={{ flexShrink: 0 }} />
    </div>
  );
}

// ── disabled live controls ───────────────────────────────────────────────────

interface LockedControl {
  label: string;
  reason: string;
}

const LOCKED_CONTROLS: LockedControl[] = [
  { label: 'Place Live Order', reason: 'Live trading is NOT LICENSED.' },
  { label: 'Enable Live Mode', reason: 'live_mode is locked false until proof + legal gates close.' },
  { label: 'Broker ACCEPT', reason: 'Broker ACCEPT is NOT LICENSED and is not created by owner approval.' },
  { label: 'Auto-Deposit', reason: 'Auto-deposit / pre-funded pull is NOT LICENSED.' },
  { label: 'Withdraw to Bank / Card', reason: 'Debit/card/bank transfer is NOT LICENSED.' },
  { label: 'Payout Automation', reason: 'Payout automation is NOT LICENSED.' },
];

const lockedBtnStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 4,
  alignItems: 'flex-start',
  textAlign: 'left',
  padding: '10px 12px',
  borderRadius: 6,
  border: '1px solid rgba(248, 113, 113, 0.25)',
  background: 'rgba(248, 113, 113, 0.05)',
  color: COLORS.textMuted,
  cursor: 'not-allowed',
  width: '100%',
  font: 'inherit',
  opacity: 0.85,
};

function LockedControlButton({ control }: { control: LockedControl }) {
  return (
    <button type="button" disabled aria-disabled="true" style={lockedBtnStyle} title={control.reason}>
      <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span aria-hidden="true">🔒</span>
        <span style={{ fontSize: 12.5, fontWeight: 600, color: COLORS.textSecondary }}>{control.label}</span>
      </span>
      <span style={{ fontSize: 11, color: COLORS.textMuted }}>{control.reason}</span>
    </button>
  );
}

// ── states ───────────────────────────────────────────────────────────────────

const centerStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  minHeight: 240,
  color: COLORS.textSecondary,
  fontSize: 13,
};

export function ForexProofPage() {
  const [bundle, setBundle] = useState<ForexProofBundle | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchForexProofBundle()
      .then((b) => {
        if (!cancelled) setBundle(b);
      })
      .catch((e: unknown) => {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Failed to load CAS Forex evidence.');
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (error) {
    return (
      <div style={centerStyle} role="alert">
        Could not load CAS Forex proof evidence: {error}
      </div>
    );
  }

  if (!bundle) {
    return (
      <div style={centerStyle} role="status" aria-live="polite">
        <motion.span
          animate={{ opacity: [0.4, 1, 0.4] }}
          transition={{ duration: 1.4, repeat: Infinity, ease: 'easeInOut' }}
        >
          Loading CAS Forex proof evidence…
        </motion.span>
      </div>
    );
  }

  const report = bundle.paperProof.report;
  const summary = report.daily_summaries[report.daily_summaries.length - 1];
  const r = bundle.uiReadiness;
  const schedule = bundle.schedule;
  const eligibility = deriveLiveEligibility(bundle);

  return (
    <motion.div
      style={stackStyle}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={SPRING_GENTLE}
    >
      <ForexModeBanner bundle={bundle} />

      <ForexPanel
        title="Active Lead"
        subtitle="The strongest current candidate under paper proof. Research lead only — not a live system."
        aside={<ForexStatusChip label="timeframe" value={summary?.timeframe ?? r.timeframe} tone="neutral" />}
      >
        <div style={defGridStyle}>
          <Def k="lead" v={r.lead_id} />
          <Def k="setting" v={r.strategy_setting} />
          <Def k="symbols" v={report.symbols.join(', ')} />
          <Def k="broker mode" v={summary?.broker_mode ?? '—'} />
          <Def k="terminal" v={summary ? `${summary.terminal_name} · ${summary.server}` : '—'} />
          <Def k="trading edge" v={<ClaimStatusChip status="OPEN" title="No cost-surviving edge proven yet." />} />
        </div>
      </ForexPanel>

      <ForexPanel
        title="Paper Session Evidence"
        subtitle="Daily evidence that the system would have acted safely in demo/paper mode. Not live permission, not income proof."
        aside={
          <ForexStatusChip
            label="paper days"
            value={`${report.completed_trading_days} / ${report.required_trading_days}`}
            tone="amber"
          />
        }
      >
        <div style={defGridStyle}>
          <Def k="latest day" v={summary ? `${summary.date} (day ${summary.trading_day})` : '—'} />
          <Def
            k="receipt level"
            v={summary ? <ClaimStatusChip status={summary.receipt_validation_status === 'BROKER_API_VERIFIED' ? 'VERIFIED' : summary.receipt_validation_status} /> : '—'}
          />
          <Def k="orders attempted" v={summary?.orders_attempted ?? '—'} />
          <Def k="orders paper-executed" v={summary?.orders_paper_executed ?? '—'} />
          <Def
            k="open positions"
            v={report.open_positions_reconciled ? 'reconciled' : 'unreconciled'}
          />
          <Def k="live mode used" v={String(report.live_mode_used)} />
        </div>

        <div style={{ marginTop: 14 }}>
          <div style={{ fontSize: 11, color: COLORS.textMuted, marginBottom: 4, letterSpacing: 0.4 }}>
            EVIDENCE CHAIN · {report.packet_count} packet(s)
          </div>
          {summary ? (
            <>
              <EvidenceHashRow
                label="broker receipt sha256"
                hash={summary.broker_receipt_hash_sha256}
                verified={summary.broker_receipt_validated}
              />
              <EvidenceHashRow label="broker export sha256" hash={summary.broker_export_sha256} verified={summary.broker_source_verified} />
              <EvidenceHashRow label="account id hash" hash={summary.account_id_hash} />
            </>
          ) : null}
          <EvidenceHashRow
            label="local hash chain"
            hash={report.chain_verified ? 'verified' : 'unverified'}
            verified={report.chain_verified}
          />
        </div>
      </ForexPanel>

      <ForexPanel
        title="Live Eligibility Checklist"
        subtitle="Every gate that must close before a live-money path can even be reconsidered."
      >
        <div>
          {eligibility.map((row) => (
            <EligibilityRowView key={row.key} row={row} />
          ))}
        </div>
      </ForexPanel>

      <ForexPanel
        title="Multi-Day Proof Maturity"
        subtitle="Complete daily bundles let the UI truthfully claim multi-day maturity. This is separate from the 30-day live-money gate."
        aside={
          <ForexStatusChip
            label="bundles"
            value={`${r.complete_bundle_days} / ${r.min_daily_bundles_for_ui}`}
            tone={r.readiness_status === 'READY_FOR_UI_UX' ? 'teal' : 'amber'}
          />
        }
      >
        <div style={{ marginBottom: 10 }}>
          <ClaimStatusChip status={r.readiness_status === 'READY_FOR_UI_UX' ? 'READY_FOR_UI_UX' : 'OPEN'} />
        </div>
        <LockReasonList reasons={r.blockers} emptyLabel="All multi-day maturity gates met." glyph="•" />
        <p style={{ fontSize: 11.5, color: COLORS.textMuted, marginTop: 10, marginBottom: 0, lineHeight: 1.5 }}>
          {r.next_ui_step}
        </p>
      </ForexPanel>

      <ForexPanel
        title="Next Action"
        subtitle="Operator prompt only. It does not place trades, create broker ACCEPT, or authorize live money."
        aside={<ClaimStatusChip status={schedule.next_due_status} />}
      >
        <div style={defGridStyle}>
          <Def k="as of" v={schedule.as_of_date} />
          <Def k="next due" v={schedule.next_due_date} />
          <Def k="paper days remaining" v={`${schedule.paper_days_remaining} / ${schedule.required_paper_days}`} />
          <Def k="missing tracks" v={schedule.missing_tracks_for_next_due.join(', ')} />
        </div>
        <div style={{ marginTop: 12 }}>
          <div style={{ fontSize: 11, color: COLORS.textMuted, marginBottom: 4, letterSpacing: 0.4 }}>
            RECOMMENDED COMMAND
          </div>
          <code style={monoBlockStyle} data-testid="recommended-command">
            {schedule.recommended_command}
          </code>
        </div>
      </ForexPanel>

      <ForexPanel
        title="Live & Payment Controls"
        subtitle="All disabled by design. Owner approval never creates broker ACCEPT or live/payment permission."
        aside={<ClaimStatusChip status="NOT LICENSED" />}
      >
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))',
            gap: 10,
          }}
        >
          {LOCKED_CONTROLS.map((control) => (
            <LockedControlButton key={control.label} control={control} />
          ))}
        </div>
      </ForexPanel>

      <p
        style={{
          fontSize: 11,
          color: COLORS.textFaint,
          textAlign: 'center',
          margin: '4px 0 0',
          lineHeight: 1.6,
        }}
      >
        <span style={{ color: ACCENT_TEAL }}>Read-only proof cockpit.</span>{' '}
        {bundle.paperProof.claim_boundary}
      </p>
    </motion.div>
  );
}

export default ForexProofPage;
