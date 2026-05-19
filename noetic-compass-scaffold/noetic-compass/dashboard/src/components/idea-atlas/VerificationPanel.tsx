/**
 * VerificationPanel — renders a single node's CAS Verification Stack
 * verdict inside the Atlas trace detail panel.
 *
 * Data source: `NodeVerification` from `lib/trace.ts`, which mirrors the
 * Stage 19A Stack JSON at
 * `research/cas_probe/stage19a_formula_verification_stack_20260519.json`.
 *
 * Reserved language: this surface uses the Stack's own vocabulary —
 * "accepted", "suppressed", "decision_tier", "suppression reasons" —
 * never "rejected", "failed", or "skipped". The decision_tier badge
 * color encoding matches the Stack spec sheet:
 *   - high      → green   (clean accept, ensemble agrees)
 *   - medium    → yellow  (accept with caveat)
 *   - suppress  → red     (Stack refused to surface this node)
 *   - uncertain → gray    (Stack has not rendered a verdict)
 *
 * Component is pure-presentational and renders nothing when the node
 * has no `verification` field, so existing trace fixtures keep working.
 */
import type { NodeVerification } from '../../lib/trace';

export interface VerificationPanelProps {
  verification: NodeVerification | null | undefined;
  /** Optional className passthrough so the parent panel can position. */
  className?: string;
}

interface TierStyle {
  /** Tailwind class strings tuned to match the Stack spec sheet. */
  badgeBg: string;
  badgeText: string;
  badgeBorder: string;
  sectionBorder: string;
  sectionBg: string;
  label: string;
}

const TIER_STYLES: Record<NonNullable<NodeVerification['decision_tier']>, TierStyle> = {
  high: {
    badgeBg: 'bg-emerald-500/20',
    badgeText: 'text-emerald-300',
    badgeBorder: 'border-emerald-400/40',
    sectionBorder: 'border-emerald-500/25',
    sectionBg: 'bg-emerald-500/[0.04]',
    label: 'HIGH',
  },
  medium: {
    badgeBg: 'bg-amber-500/20',
    badgeText: 'text-amber-300',
    badgeBorder: 'border-amber-400/40',
    sectionBorder: 'border-amber-500/25',
    sectionBg: 'bg-amber-500/[0.04]',
    label: 'MEDIUM',
  },
  suppress: {
    badgeBg: 'bg-rose-500/20',
    badgeText: 'text-rose-300',
    badgeBorder: 'border-rose-400/40',
    sectionBorder: 'border-rose-500/25',
    sectionBg: 'bg-rose-500/[0.04]',
    label: 'SUPPRESS',
  },
  uncertain: {
    badgeBg: 'bg-slate-500/20',
    badgeText: 'text-slate-300',
    badgeBorder: 'border-slate-400/40',
    sectionBorder: 'border-slate-500/25',
    sectionBg: 'bg-slate-500/[0.04]',
    label: 'UNCERTAIN',
  },
};

function tierStyleFor(
  tier: NodeVerification['decision_tier'] | undefined,
): TierStyle {
  if (tier && tier in TIER_STYLES) {
    return TIER_STYLES[tier as keyof typeof TIER_STYLES];
  }
  return TIER_STYLES.uncertain;
}

/** Pretty-print a suppression reason code like "final_token_conflicted". */
function formatReasonChipLabel(reason: string): string {
  return reason.replace(/_/g, ' ');
}

export function VerificationPanel({
  verification,
  className,
}: VerificationPanelProps) {
  // Missing field is a valid state — pre-Stack traces have no verdict.
  // Render nothing so the rest of the detail panel is undisturbed.
  if (!verification) return null;

  const tier = verification.decision_tier ?? 'uncertain';
  const style = tierStyleFor(tier);
  const decision = verification.decision;
  const isSuppressed = decision === 'SUPPRESS' || tier === 'suppress';
  const isAccepted = decision === 'ACCEPT' && !isSuppressed;

  return (
    <section
      data-testid="verification-panel"
      data-decision-tier={tier}
      data-decision={decision ?? 'null'}
      className={[
        'mt-4 rounded border p-3',
        style.sectionBorder,
        style.sectionBg,
        className ?? '',
      ]
        .filter(Boolean)
        .join(' ')}
    >
      <div className="mb-2 flex items-center justify-between gap-2">
        <div className="text-accent-teal text-xs font-bold">VERIFICATION</div>
        <span
          data-testid="verification-tier-badge"
          className={[
            'rounded border px-2 py-0.5 font-mono text-[10px] font-bold uppercase tracking-wider',
            style.badgeBg,
            style.badgeText,
            style.badgeBorder,
          ].join(' ')}
        >
          {style.label}
        </span>
      </div>

      <dl className="space-y-2">
        <div>
          <dt className="text-slate-500 text-[10px] uppercase">decision</dt>
          <dd
            data-testid="verification-decision"
            className="text-slate-100 font-mono text-[11px]"
          >
            {decision === 'ACCEPT'
              ? 'accepted'
              : decision === 'SUPPRESS'
                ? 'suppressed'
                : 'no verdict'}
          </dd>
        </div>

        {isAccepted && (
          <>
            {typeof verification.confidence === 'number' && (
              <div>
                <dt className="text-slate-500 text-[10px] uppercase">
                  confidence band
                </dt>
                <dd
                  data-testid="verification-confidence"
                  className="text-slate-200 font-mono text-[11px]"
                >
                  {verification.confidence.toFixed(2)}
                </dd>
              </div>
            )}
            {typeof verification.ensemble_agreement === 'boolean' && (
              <div>
                <dt className="text-slate-500 text-[10px] uppercase">
                  ensemble agreement
                </dt>
                <dd
                  data-testid="verification-ensemble-agreement"
                  className={
                    verification.ensemble_agreement
                      ? 'text-emerald-300 font-mono text-[11px]'
                      : 'text-amber-300 font-mono text-[11px]'
                  }
                >
                  {verification.ensemble_agreement ? 'true' : 'false'}
                </dd>
              </div>
            )}
          </>
        )}

        {isSuppressed && (
          <div>
            <dt className="text-slate-500 text-[10px] uppercase">
              suppression reasons
            </dt>
            <dd
              data-testid="verification-suppression-reasons"
              className="mt-1 flex flex-wrap gap-1.5"
            >
              {verification.suppression_reasons &&
              verification.suppression_reasons.length > 0 ? (
                verification.suppression_reasons.map((reason, i) => (
                  <span
                    key={`${reason}-${i}`}
                    data-testid="verification-suppression-chip"
                    data-reason={reason}
                    className="rounded border border-rose-400/40 bg-rose-500/15 px-2 py-0.5 font-mono text-[10px] text-rose-200"
                  >
                    {formatReasonChipLabel(reason)}
                  </span>
                ))
              ) : (
                <span className="text-slate-500 italic font-mono text-[11px]">
                  no reason codes recorded
                </span>
              )}
            </dd>
          </div>
        )}
      </dl>
    </section>
  );
}

export default VerificationPanel;
