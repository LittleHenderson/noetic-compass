// Always-visible CAS Forex status banner. Surfaces mode, paper/live state,
// evidence-chain health, proof progress, and the three NOT LICENSED boundaries
// at all times. By construction it cannot show a green LIVE state on day-1
// evidence: live_mode is read from evidence (false) and the mode is clamped to
// the paper/sim/locked set.

import type { CSSProperties } from 'react';
import { GlassPanel } from '../../components/ui/GlassPanel';
import { COLORS, ACCENT_TEAL } from '../../lib/designTokens';
import { deriveBannerState } from '../forexSelectors';
import type { ForexProofBundle } from '../types';
import { ClaimStatusChip } from './ClaimStatusChip';
import { ForexStatusChip } from './ForexStatusChip';
import { chipStyle } from './chipStyles';

export interface ForexModeBannerProps {
  bundle: ForexProofBundle;
}

const rowStyle: CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  alignItems: 'center',
  gap: 8,
};

const dotStyle = (live: boolean): CSSProperties => ({
  width: 8,
  height: 8,
  borderRadius: '50%',
  // Amber pulse for paper/locked; never green unless genuinely live (it isn't).
  background: live ? ACCENT_TEAL : '#fbbf24',
  boxShadow: live ? `0 0 8px ${ACCENT_TEAL}` : '0 0 8px rgba(251,191,36,0.6)',
  flexShrink: 0,
});

export function ForexModeBanner({ bundle }: ForexModeBannerProps) {
  const s = deriveBannerState(bundle);

  return (
    <GlassPanel intensity="regular" padding="12px 16px" ariaLabel="CAS Forex status banner" style={{ width: '100%' }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <div style={{ ...rowStyle, justifyContent: 'space-between' }}>
          <div style={rowStyle}>
            <span style={dotStyle(s.liveMode)} aria-hidden="true" />
            <span style={chipStyle(s.liveMode ? 'danger' : 'amber')}>{s.mode}</span>
            <ForexStatusChip
              label="paper_trading"
              value={String(s.paperTrading)}
              tone="teal"
            />
            <ForexStatusChip
              label="live_mode"
              value={String(s.liveMode)}
              tone={s.liveMode ? 'danger' : 'muted'}
            />
          </div>
          {s.fromFixtures ? (
            <span
              style={chipStyle('muted')}
              title="Served from bundled day-1 evidence fixtures; no live backend is wired yet."
            >
              FIXTURE DATA
            </span>
          ) : null}
        </div>

        <div style={rowStyle}>
          <ForexStatusChip
            label="paper proof"
            value={`${s.paperProof.completed} / ${s.paperProof.required}`}
            tone="amber"
            title="Verified paper trading days toward the 30-day live-money promotion gate."
          />
          <ForexStatusChip
            label="multi-day maturity"
            value={`${s.multiDayMaturity.complete} / ${s.multiDayMaturity.required}`}
            tone={s.multiDayMaturity.ready ? 'teal' : 'amber'}
            title="Complete daily bundles toward the UI multi-day proof-maturity claim."
          />
          <ForexStatusChip
            label="evidence chain"
            value={s.evidenceChainVerified ? 'verified' : 'unverified'}
            tone={s.evidenceChainVerified ? 'teal' : 'danger'}
          />
          <ForexStatusChip
            label="live lock"
            value={s.liveLockActive ? 'active' : 'none'}
            tone={s.liveLockActive ? 'danger' : 'muted'}
          />
        </div>

        <div style={{ ...rowStyle, gap: 6 }}>
          <span style={{ fontSize: 11, color: COLORS.textMuted, marginRight: 2 }}>Live boundaries:</span>
          <ClaimStatusChip status={s.deploymentStatus} title="Deployment status" />
          <span style={{ fontSize: 11, color: COLORS.textMuted }}>broker ACCEPT</span>
          <ClaimStatusChip status={s.brokerAcceptStatus} title="Broker ACCEPT status" />
          <span style={{ fontSize: 11, color: COLORS.textMuted }}>payment transfer</span>
          <ClaimStatusChip status={s.paymentTransferStatus} title="Payment transfer status" />
        </div>
      </div>
    </GlassPanel>
  );
}

export default ForexModeBanner;
