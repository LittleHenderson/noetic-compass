import type { CSSProperties } from 'react';
import {
  COLORS,
  EASE_OUT_CUBIC,
  FONT_FAMILY,
  FONT_MONO,
  TONE_TINT,
  type StageNodeState,
} from '../../lib/designTokens';
import type { AuditLifecycleStatus } from './AuditSessionProgress';
import type { AuditVerdict } from '../../lib/casHarnessAudit';

export interface AuditStageLadderProps {
  status: AuditLifecycleStatus;
  /** Present verdict; gates the final node into the teal "Completed" terminal. */
  verdict?: AuditVerdict | null;
  className?: string;
}

// Six public nodes over the unchanged backend lifecycle union (plan §4 table).
// Index is the canonical left -> right order on the hairline track.
const STAGE_NODES = [
  { key: 'queued', label: 'Queued' },
  { key: 'validating', label: 'Validating' },
  { key: 'running', label: 'Running' },
  { key: 'verifying', label: 'Verifying' },
  { key: 'anchoring', label: 'Anchoring' },
  { key: 'completed', label: 'Completed' },
] as const;

const RUNNING_INDEX = 2;
const FINAL_INDEX = STAGE_NODES.length - 1;

// Maps the internal lifecycle status to the index of the node it has reached.
// evidence_pending spans Verifying(3) + Anchoring(4); we treat the run as
// having reached Anchoring so Verifying reads done and Anchoring reads active.
function reachedIndexFor(status: AuditLifecycleStatus): number {
  switch (status) {
    case 'draft':
      return 0;
    case 'validating':
      return 1;
    case 'running':
    case 'runner_pending':
      return 2;
    case 'evidence_pending':
      return 4;
    case 'complete':
      return 5;
    case 'failed':
      // The failure halts wherever the run stopped; without finer signal we
      // surface it on the Running node (the last node guaranteed to have begun).
      return 2;
  }
}

type ResolvedNode = {
  key: string;
  label: string;
  state: StageNodeState;
  interrupt?: string;
};

function resolveNodes(
  status: AuditLifecycleStatus,
  verdict: AuditVerdict | null | undefined,
): ResolvedNode[] {
  const reached = reachedIndexFor(status);
  const failed = status === 'failed';
  const flagged = verdict === 'FLAG_FOR_HUMAN_REVIEW';
  // A clean teal "Completed" requires BOTH complete status AND a verdict.
  const completedClean = status === 'complete' && Boolean(verdict);

  return STAGE_NODES.map((node, index) => {
    // Terminal node overrides.
    if (index === FINAL_INDEX) {
      if (failed) {
        return { ...node, label: 'Failed', state: 'failed' };
      }
      if (flagged) {
        return { ...node, label: 'Needs human review', state: 'review' };
      }
      if (completedClean) {
        return { ...node, label: node.label, state: 'done' };
      }
      // Reached evidence/complete-without-verdict but not a clean completion:
      // keep the node pending rather than implying a finished verdict.
      return { ...node, label: node.label, state: 'pending' };
    }

    if (failed) {
      if (index < reached) return { ...node, label: node.label, state: 'done' };
      if (index === reached) return { ...node, label: node.label, state: 'failed' };
      return { ...node, label: node.label, state: 'pending' };
    }

    // runner_pending is NOT a normal stage advance — it pins an amber interrupt
    // on the Running node ("Runner not connected") and stops there.
    if (status === 'runner_pending' && index === RUNNING_INDEX) {
      return {
        ...node,
        label: node.label,
        state: 'review',
        interrupt: 'Runner not connected',
      };
    }

    if (index < reached) return { ...node, label: node.label, state: 'done' };
    if (index === reached) return { ...node, label: node.label, state: 'active' };
    return { ...node, label: node.label, state: 'pending' };
  });
}

const trackWrapStyle: CSSProperties = {
  display: 'grid',
  gap: 12,
  fontFamily: FONT_FAMILY,
};

const railStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: `repeat(${STAGE_NODES.length}, minmax(0, 1fr))`,
  gap: 6,
  alignItems: 'start',
};

const nodeColumnStyle: CSSProperties = {
  display: 'grid',
  justifyItems: 'center',
  gap: 8,
  textAlign: 'center',
  minWidth: 0,
};

function dotStyle(state: StageNodeState): CSSProperties {
  const tone = TONE_TINT[state === 'pending' ? 'muted' : tintKey(state)];
  const active = state === 'active';
  return {
    width: 16,
    height: 16,
    borderRadius: '50%',
    border: `2px solid ${state === 'pending' ? COLORS.borderStrong : tone.accent}`,
    background: state === 'pending' ? 'rgba(255, 255, 255, 0.03)' : tone.fill,
    boxShadow: state === 'done' ? `0 0 0 3px ${tone.fillSoft}` : 'none',
    // Only the single active node breathes, on the brand 2.5s heartbeat.
    animation: active ? 'cas-step-breathe 2.5s ease-in-out infinite alternate' : undefined,
  };
}

function tintKey(state: StageNodeState): 'teal' | 'amber' | 'rose' | 'muted' {
  if (state === 'done') return 'teal';
  if (state === 'active' || state === 'review') return 'amber';
  if (state === 'failed') return 'rose';
  return 'muted';
}

const connectorStyle = (filled: boolean): CSSProperties => ({
  height: 2,
  flex: 1,
  marginTop: 7,
  borderRadius: 2,
  background: filled ? TONE_TINT.teal.border : COLORS.borderSubtle,
  transition: `background 0.4s cubic-bezier(${EASE_OUT_CUBIC.join(',')})`,
});

const labelStyle = (state: StageNodeState): CSSProperties => ({
  fontSize: 11,
  fontWeight: 700,
  lineHeight: 1.25,
  color:
    state === 'pending'
      ? COLORS.textMuted
      : state === 'done'
        ? COLORS.textPrimary
        : TONE_TINT[tintKey(state)].text,
});

const interruptPillStyle: CSSProperties = {
  display: 'inline-block',
  marginTop: 2,
  padding: '2px 6px',
  borderRadius: 4,
  border: `1px solid ${TONE_TINT.amber.border}`,
  background: TONE_TINT.amber.fillSoft,
  color: TONE_TINT.amber.text,
  fontFamily: FONT_MONO,
  fontSize: 9.5,
  fontWeight: 800,
  textTransform: 'uppercase',
  letterSpacing: 0.3,
};

/**
 * Horizontal stage ladder — the visible beginning -> middle -> end of a run.
 * Maps the unchanged backend lifecycle onto six public nodes. The single active
 * node pulses on the brand heartbeat; done nodes are teal, the runner-pending
 * interrupt and FLAG terminal are amber, a failed terminal is rose. Color is
 * never the only signal — every node carries its word.
 */
export function AuditStageLadder({
  status,
  verdict = null,
  className,
}: AuditStageLadderProps): JSX.Element {
  const nodes = resolveNodes(status, verdict);

  return (
    <div style={trackWrapStyle} className={className} aria-label="Audit stage ladder">
      <ol style={railStyle}>
        {nodes.map((node, index) => {
          const reachedThis = node.state === 'done' || node.state === 'active';
          const connectorFilled =
            index > 0 && (nodes[index - 1].state === 'done' || node.state === 'done');
          return (
            <li
              key={node.key}
              style={nodeColumnStyle}
              data-state={node.state}
              aria-current={node.state === 'active' ? 'step' : undefined}
            >
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  width: '100%',
                  justifyContent: 'center',
                }}
              >
                {index > 0 ? <span aria-hidden="true" style={connectorStyle(connectorFilled)} /> : <span style={{ flex: 1 }} />}
                <span
                  aria-hidden="true"
                  className={node.state === 'active' ? 'cas-step-breathe' : undefined}
                  style={dotStyle(node.state)}
                />
                {index < nodes.length - 1 ? (
                  <span aria-hidden="true" style={connectorStyle(reachedThis && nodes[index + 1].state === 'done')} />
                ) : (
                  <span style={{ flex: 1 }} />
                )}
              </div>
              <span style={labelStyle(node.state)}>{node.label}</span>
              {node.interrupt ? (
                <span role="note" aria-label={node.interrupt} style={interruptPillStyle}>
                  {node.interrupt}
                </span>
              ) : null}
            </li>
          );
        })}
      </ol>
    </div>
  );
}

export default AuditStageLadder;
