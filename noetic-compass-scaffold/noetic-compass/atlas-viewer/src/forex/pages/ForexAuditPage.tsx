// /forex/audit — the CAS Forex Audit Console.
//
// Trace-by-trace view of the pipeline and evidence chain for the real day-1
// paper route candidates. Read-only: it replays recorded evidence, it does not
// run anything. Every trace ends SUPPRESSED with no broker order placed.

import { useEffect, useMemo, useState, type CSSProperties } from 'react';
import { motion } from 'framer-motion';
import { COLORS, ACCENT_TEAL, SPRING_GENTLE, SPRING_SNAPPY } from '../../lib/designTokens';
import { fetchForexProofBundle } from '../forexApi';
import { deriveTraces } from '../forexSelectors';
import type { ForexProofBundle, ForexTrace } from '../types';
import { ForexModeBanner } from '../components/ForexModeBanner';
import { ForexPanel } from '../components/ForexPanel';
import { ForexStatusChip } from '../components/ForexStatusChip';
import { ClaimStatusChip } from '../components/ClaimStatusChip';
import { EvidenceHashRow } from '../components/EvidenceHashRow';
import { TraceStageList } from '../components/TraceStageList';
import { chipStyle, toneForStage } from '../components/chipStyles';

const stackStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 14,
  width: '100%',
};

const centerStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  minHeight: 240,
  color: COLORS.textSecondary,
  fontSize: 13,
};

const traceCardStyle = (active: boolean): CSSProperties => ({
  position: 'relative',
  display: 'flex',
  flexDirection: 'column',
  gap: 6,
  alignItems: 'flex-start',
  textAlign: 'left',
  padding: '10px 12px',
  borderRadius: 6,
  border: `1px solid ${active ? 'rgba(45, 212, 191, 0.35)' : COLORS.borderSubtle}`,
  background: active ? 'rgba(45, 212, 191, 0.06)' : 'rgba(255,255,255,0.02)',
  color: COLORS.textPrimary,
  cursor: 'pointer',
  font: 'inherit',
  width: '100%',
});

const defGridStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'minmax(110px, max-content) 1fr',
  rowGap: 8,
  columnGap: 16,
  fontSize: 12.5,
};

const defKeyStyle: CSSProperties = { color: COLORS.textMuted };
const defValStyle: CSSProperties = { color: COLORS.textPrimary, fontWeight: 600 };

export function ForexAuditPage() {
  const [bundle, setBundle] = useState<ForexProofBundle | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);

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

  const traces = useMemo<ForexTrace[]>(() => (bundle ? deriveTraces(bundle) : []), [bundle]);
  const selected = traces.find((t) => t.trace_id === selectedId) ?? traces[0] ?? null;

  if (error) {
    return (
      <div style={centerStyle} role="alert">
        Could not load CAS Forex audit evidence: {error}
      </div>
    );
  }

  if (!bundle || !selected) {
    return (
      <div style={centerStyle} role="status" aria-live="polite">
        <motion.span
          animate={{ opacity: [0.4, 1, 0.4] }}
          transition={{ duration: 1.4, repeat: Infinity, ease: 'easeInOut' }}
        >
          Loading CAS Forex audit traces…
        </motion.span>
      </div>
    );
  }

  return (
    <motion.div style={stackStyle} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={SPRING_GENTLE}>
      <ForexModeBanner bundle={bundle} />

      <ForexPanel
        title="Audit Traces"
        subtitle="Recorded paper route candidates from the latest evidence day. Read-only replay — nothing is executed."
        aside={<ForexStatusChip label="traces" value={traces.length} tone="neutral" />}
      >
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 10 }}>
          {traces.map((t) => {
            const active = t.trace_id === selected.trace_id;
            return (
              <button
                key={t.trace_id}
                type="button"
                style={traceCardStyle(active)}
                aria-pressed={active}
                onClick={() => setSelectedId(t.trace_id)}
                data-testid={`trace-card-${t.symbol}`}
              >
                {active ? (
                  <motion.span
                    layoutId="audit-active-pill"
                    style={{ position: 'absolute', inset: 0, borderRadius: 6, border: `1px solid ${ACCENT_TEAL}`, opacity: 0.5, pointerEvents: 'none' }}
                    transition={SPRING_SNAPPY}
                  />
                ) : null}
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%' }}>
                  <span style={{ fontSize: 13, fontWeight: 700 }}>{t.symbol}</span>
                  <span style={chipStyle(toneForStage(t.packet_status))}>{t.packet_status}</span>
                </div>
                <span style={{ fontSize: 11.5, color: COLORS.textMuted }}>
                  {t.direction} · {t.date} · {t.timeframe}
                </span>
              </button>
            );
          })}
        </div>
      </ForexPanel>

      <ForexPanel
        title={`Pipeline · ${selected.symbol}`}
        subtitle="Forecast Harness → Gate 0-4 → Broker → Post-Trade → Evidence → Live Lock. Dimmed stages were not exercised in the day-1 paper-route loop."
        aside={<ClaimStatusChip status={selected.route_action} />}
      >
        <div style={{ ...defGridStyle, marginBottom: 14 }}>
          <span style={defKeyStyle}>trace id</span>
          <span style={{ ...defValStyle, wordBreak: 'break-all', fontSize: 11.5 }}>{selected.trace_id}</span>
          <span style={defKeyStyle}>confidence</span>
          <span style={defValStyle}>{selected.confidence.toFixed(4)}</span>
          <span style={defKeyStyle}>sized lots</span>
          <span style={defValStyle}>{selected.sized_lots ?? '—'}</span>
          <span style={defKeyStyle}>planned risk</span>
          <span style={defValStyle}>{selected.planned_risk_usd != null ? `$${selected.planned_risk_usd}` : '—'}</span>
        </div>
        <TraceStageList stages={selected.stages} />
      </ForexPanel>

      <ForexPanel
        title="Evidence Packet"
        subtitle="Local append-only hash chain. No WORM/Object-Lock retention is wired for CAS Forex yet."
        aside={<span style={chipStyle(toneForStage(selected.packet_status))}>{selected.packet_status}</span>}
      >
        <div style={{ ...defGridStyle, marginBottom: 12 }}>
          <span style={defKeyStyle}>broker order placed</span>
          <span style={defValStyle}>{selected.broker_order_placed ? 'yes' : 'no'}</span>
          <span style={defKeyStyle}>chain verified</span>
          <span style={defValStyle}>{selected.chain_verified ? 'true' : 'false'}</span>
        </div>
        <div>
          {selected.hashes.map((h) => (
            <EvidenceHashRow key={h.label} label={h.label} hash={h.hash} verified={h.verified} />
          ))}
          <EvidenceHashRow
            label="local hash chain"
            hash={selected.chain_verified ? 'verified' : 'unverified'}
            verified={selected.chain_verified}
          />
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 12 }}>
          <span style={{ fontSize: 11, color: COLORS.textMuted }}>WORM status</span>
          <ClaimStatusChip status="UNAVAILABLE" title="Local hash chain only; WORM/Object-Lock not wired." />
        </div>
      </ForexPanel>

      <p style={{ fontSize: 11, color: COLORS.textFaint, textAlign: 'center', margin: '4px 0 0', lineHeight: 1.6 }}>
        <span style={{ color: ACCENT_TEAL }}>Read-only audit replay.</span>{' '}
        {bundle.decision.claim_boundary}
      </p>
    </motion.div>
  );
}

export default ForexAuditPage;
