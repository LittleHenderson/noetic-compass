// Adaptive compounding panel for the CAS Forex proof cockpit.
// Shows the latest paper compounding decisions (OPEN_INITIAL, ADD_TO_WINNER,
// TIGHTEN_STOP, PARTIAL_TAKE_PROFIT, CLOSE_BASKET, NO_TRADE) and action counts.

import type { CSSProperties } from 'react';
import { ForexPanel } from './ForexPanel';
import { ForexStatusChip } from './ForexStatusChip';
import { COLORS } from '../../lib/designTokens';
import type { AdaptiveCockpitPayload } from '../types';

interface Props {
  cockpit: AdaptiveCockpitPayload;
}

const monoCell: CSSProperties = {
  fontFamily: "'JetBrains Mono', 'SF Mono', Menlo, monospace",
  fontSize: 11.5,
};

const defGridStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'minmax(100px, max-content) 1fr',
  rowGap: 6,
  columnGap: 14,
  fontSize: 12.5,
};

function Def({ k, v }: { k: string; v: string | number }) {
  return (
    <>
      <span style={{ color: COLORS.textMuted }}>{k}</span>
      <span style={{ color: COLORS.textPrimary, fontWeight: 600 }}>{v}</span>
    </>
  );
}

export default function AdaptiveCompoundingPanel({ cockpit }: Props) {
  const ac = cockpit.adaptive_compounding;
  const decisions = cockpit.latest_adaptive_decisions ?? [];
  const counts = cockpit.adaptive_action_counts ?? {};
  const countEntries = Object.entries(counts);

  return (
    <ForexPanel
      title="Adaptive Compounding"
      subtitle="Paper-only management: add to winner, tighten stop, partial TP, close basket. NO broker orders placed."
      aside={
        <ForexStatusChip
          label="reviews"
          value={String(ac.review_count)}
          tone={ac.review_count > 0 ? 'teal' : 'amber'}
        />
      }
    >
      {countEntries.length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 14 }}>
          {countEntries.map(([action, count]) => (
            <span
              key={action}
              style={{
                fontSize: 10.5,
                fontWeight: 600,
                padding: '3px 8px',
                borderRadius: 999,
                border: '1px solid rgba(255,255,255,0.08)',
                color: COLORS.textSecondary,
                background: 'rgba(255,255,255,0.03)',
              }}
            >
              {action}: {count}
            </span>
          ))}
        </div>
      )}

      {decisions.length > 0 ? (
        <div style={{ overflowX: 'auto' }}>
          <table
            style={{
              width: '100%',
              borderCollapse: 'collapse',
              fontSize: 12,
            }}
          >
            <thead>
              <tr>
                {['Symbol', 'Action', 'Direction', 'Lots', 'Stop', 'Target', 'Evidence', 'Reason'].map((h) => (
                  <th
                    key={h}
                    style={{
                      textAlign: 'left',
                      padding: '6px 10px',
                      borderBottom: '1px solid rgba(255,255,255,0.06)',
                      fontSize: 10.5,
                      color: COLORS.textMuted,
                      fontWeight: 600,
                      textTransform: 'uppercase',
                      letterSpacing: 0.3,
                    }}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {decisions.map((d, i) => (
                <tr key={i}>
                  <td style={{ padding: '7px 10px', borderBottom: '1px solid rgba(255,255,255,0.04)', fontWeight: 600 }}>
                    {d.symbol}
                  </td>
                  <td style={{ padding: '7px 10px', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                    <span
                      style={{
                        fontSize: 10.5,
                        fontWeight: 600,
                        padding: '2px 6px',
                        borderRadius: 4,
                        color: d.action === 'NO_TRADE' ? COLORS.textMuted : '#2dd4bf',
                        border: `1px solid ${d.action === 'NO_TRADE' ? 'rgba(255,255,255,0.06)' : 'rgba(45,212,191,0.15)'}`,
                        background: d.action === 'NO_TRADE' ? 'transparent' : 'rgba(45,212,191,0.06)',
                      }}
                    >
                      {d.action}
                    </span>
                  </td>
                  <td style={{ padding: '7px 10px', borderBottom: '1px solid rgba(255,255,255,0.04)', color: d.direction === 'LONG' ? '#34d399' : '#f87171' }}>
                    {d.direction}
                  </td>
                  <td style={{ ...monoCell, padding: '7px 10px', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                    {d.lot_size}
                  </td>
                  <td style={{ ...monoCell, padding: '7px 10px', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                    {d.stop_loss?.toFixed(2) ?? '—'}
                  </td>
                  <td style={{ ...monoCell, padding: '7px 10px', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                    {d.take_profit?.toFixed(2) ?? '—'}
                  </td>
                  <td style={{ ...monoCell, padding: '7px 10px', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                    {(d.evidence_score * 100).toFixed(0)}%
                  </td>
                  <td style={{ padding: '7px 10px', borderBottom: '1px solid rgba(255,255,255,0.04)', fontSize: 11.5, color: COLORS.textSecondary, maxWidth: 200 }}>
                    {d.reason}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div style={{ padding: 14, fontSize: 12.5, color: COLORS.textMuted }}>
          <div style={defGridStyle}>
            <Def k="adaptive chain" v={ac.chain_verified ? 'verified' : 'unverified'} />
            <Def k="claim boundary" v={ac.claim_boundary} />
          </div>
          <p style={{ marginTop: 10, fontSize: 11.5, color: COLORS.textSecondary, lineHeight: 1.5 }}>
            No adaptive compounding review has been recorded yet.
            Run <code style={{ color: COLORS.textPrimary }}>python scripts/run_adaptive_compounding_review.py</code> to review open paper positions against current market data.
          </p>
        </div>
      )}

      <div style={{ marginTop: 10, fontSize: 10.5, color: COLORS.textMuted }}>
        {ac.deployment_status} · Broker: {ac.broker_accept_status} · Payment: {ac.payment_transfer_status}
      </div>
    </ForexPanel>
  );
}
