// Vertical pipeline stepper for one audit trace. Renders the full CAS Forex
// pipeline (Forecast Harness → Gate 0-4 → Broker → Post-Trade → Evidence →
// Live Lock). Stages the day-1 paper loop did not exercise are dimmed and
// carry a NOT_RUN chip, so the view never implies a gate ran when it didn't.

import type { CSSProperties } from 'react';
import { COLORS } from '../../lib/designTokens';
import { chipStyle, toneForStage } from './chipStyles';
import type { PipelineStage } from '../types';

export interface TraceStageListProps {
  stages: PipelineStage[];
}

const rowStyle = (exercised: boolean): CSSProperties => ({
  display: 'flex',
  gap: 12,
  padding: '10px 0',
  borderBottom: `1px solid ${COLORS.borderSubtle}`,
  opacity: exercised ? 1 : 0.55,
});

const indexColStyle: CSSProperties = {
  flexShrink: 0,
  width: 22,
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
};

const indexDotStyle = (exercised: boolean): CSSProperties => ({
  width: 20,
  height: 20,
  borderRadius: '50%',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  fontSize: 10,
  fontWeight: 700,
  color: exercised ? COLORS.textPrimary : COLORS.textMuted,
  background: 'rgba(255,255,255,0.04)',
  border: `1px solid ${COLORS.borderSubtle}`,
});

export function TraceStageList({ stages }: TraceStageListProps) {
  return (
    <div data-testid="trace-stage-list">
      {stages.map((stage, i) => (
        <div key={stage.key} style={rowStyle(stage.exercised)} data-testid={`stage-${stage.key}`}>
          <div style={indexColStyle}>
            <span style={indexDotStyle(stage.exercised)}>{i}</span>
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10 }}>
              <span style={{ fontSize: 12.5, fontWeight: 600, color: COLORS.textPrimary }}>{stage.label}</span>
              <span style={chipStyle(toneForStage(stage.status))} data-status={stage.status}>
                {stage.status}
              </span>
            </div>
            <p style={{ margin: '4px 0 0', fontSize: 11.5, color: COLORS.textMuted, lineHeight: 1.45 }}>
              {stage.detail}
            </p>
          </div>
        </div>
      ))}
    </div>
  );
}

export default TraceStageList;
