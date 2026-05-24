/**
 * BlindspotsPanel — textual interpretation surface for cover hits.
 *
 * Companion to the 3D red overlay in NeuralNetScene. The overlay is the
 * spatial marker; this panel is the meaning. Per product spec:
 *
 *   Default view: show only high/medium confidence blindspots. Let
 *   advanced users expand to low confidence.
 *
 *   Best UX rule: CAS label for experts. Plain-English meaning for
 *   everyone else. The visible UI should lead with everyday language.
 *
 *   Atlas doesn't just say "this model has a blindspot." It translates
 *   the blindspot into the kind of human concern the model may be
 *   failing to consider.
 *
 * Filter rules:
 *   - High + medium are visible by default.
 *   - Low is hidden behind a "Show low-confidence (N hidden)" expand
 *     affordance.
 *   - Unavailable entries do NOT appear in this textual list at all
 *     until probe data lands — the spec is explicit about this.
 *   - The 3D red overlay still draws for ALL detected covers regardless
 *     of band (the visual marker is unconditional; only the textual
 *     interpretation is filtered).
 */

import { useMemo, useState } from 'react';
import type { CSSProperties } from 'react';

import BlindspotInterpretation from './BlindspotInterpretation';
import {
  normaliseCoverMember,
  type NeuronCoverMember,
  type RawNeuronCoverMember,
} from '../../lib/atlasLiveApi';
import { BAND_DEFAULT_VISIBLE, type ConfidenceBand } from '../../lib/confidenceBands';
import {
  parseDriveClassKey,
  type DriveId,
  type RegisterId,
} from '../../lib/driveTranslations';

export interface BlindspotsPanelProps {
  /**
   * Cover sets, keyed by CAS class (e.g. "F1A", "F5T"). Accepts both
   * the new typed-member shape and the legacy bare-string shape so the
   * panel can render against either live or offline traces.
   */
  perClassNeuronCovers?: Record<string, RawNeuronCoverMember[] | undefined>;
  /**
   * Optional override for which bands are visible. Defaults to
   * BAND_DEFAULT_VISIBLE (high + medium).
   */
  defaultVisibleBands?: readonly ConfidenceBand[];
}

interface AggregatedClass {
  classKey: string;
  driveId: DriveId;
  register: RegisterId | null;
  bestBand: ConfidenceBand;
  bestConfidence: number | null;
  evidenceSources: string[];
  memberCount: number;
}

const BAND_RANK: Record<ConfidenceBand, number> = {
  high: 3,
  medium: 2,
  low: 1,
  unavailable: 0,
};

function maxBand(a: ConfidenceBand, b: ConfidenceBand): ConfidenceBand {
  return BAND_RANK[a] >= BAND_RANK[b] ? a : b;
}

/**
 * Roll up the per-neuron members in a single cover class to ONE row in
 * the panel. We aggregate so we don't print the same plain-English
 * sentence once per neuron — that would be noise. The aggregate keeps
 * the strongest band + the highest confidence + the union of evidence
 * sources across all members in the class.
 */
function aggregateClass(
  classKey: string,
  members: NeuronCoverMember[],
): AggregatedClass | null {
  const parsed = parseDriveClassKey(classKey);
  if (!parsed) return null;
  let bestBand: ConfidenceBand = 'unavailable';
  let bestConfidence: number | null = null;
  const evidenceSet = new Set<string>();
  for (const m of members) {
    bestBand = maxBand(bestBand, m.confidence_band);
    if (m.confidence !== null) {
      if (bestConfidence === null || m.confidence > bestConfidence) {
        bestConfidence = m.confidence;
      }
    }
    for (const src of m.evidence_sources) evidenceSet.add(src);
  }
  return {
    classKey,
    driveId: parsed.driveId,
    register: parsed.register,
    bestBand,
    bestConfidence,
    evidenceSources: Array.from(evidenceSet),
    memberCount: members.length,
  };
}

const panelStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 10,
};

const headerStyle: CSSProperties = {
  fontSize: 11,
  textTransform: 'uppercase',
  letterSpacing: '0.08em',
  color: '#94a3b8',
  fontWeight: 700,
  margin: 0,
};

const emptyStyle: CSSProperties = {
  margin: 0,
  fontSize: 12,
  color: '#94a3b8',
  fontStyle: 'italic',
  padding: '8px 12px',
  borderRadius: 6,
  background: 'rgba(15, 23, 42, 0.45)',
  border: '1px solid rgba(255,255,255,0.04)',
};

const expandButtonStyle: CSSProperties = {
  alignSelf: 'flex-start',
  background: 'rgba(15, 23, 42, 0.6)',
  border: '1px solid rgba(148, 163, 184, 0.25)',
  color: '#cbd5e1',
  fontSize: 11,
  padding: '4px 10px',
  borderRadius: 12,
  cursor: 'pointer',
  letterSpacing: 0.3,
};

export default function BlindspotsPanel(
  props: BlindspotsPanelProps,
): JSX.Element {
  const { perClassNeuronCovers, defaultVisibleBands = BAND_DEFAULT_VISIBLE } = props;
  const [expanded, setExpanded] = useState(false);

  const aggregated = useMemo<AggregatedClass[]>(() => {
    if (!perClassNeuronCovers) return [];
    const out: AggregatedClass[] = [];
    for (const [classKey, rawMembers] of Object.entries(perClassNeuronCovers)) {
      const normalised = (rawMembers ?? []).map(normaliseCoverMember);
      const agg = aggregateClass(classKey, normalised);
      if (agg) out.push(agg);
    }
    // Stable sort: stronger bands first, then by class key.
    out.sort((a, b) => {
      const rank = BAND_RANK[b.bestBand] - BAND_RANK[a.bestBand];
      if (rank !== 0) return rank;
      return a.classKey.localeCompare(b.classKey);
    });
    return out;
  }, [perClassNeuronCovers]);

  const visibleBands = expanded
    ? new Set<ConfidenceBand>([...defaultVisibleBands, 'low'])
    : new Set<ConfidenceBand>(defaultVisibleBands);
  // Unavailable NEVER appears in this textual panel — per spec.
  visibleBands.delete('unavailable');

  const visible = aggregated.filter((a) => visibleBands.has(a.bestBand));
  const hiddenLow = aggregated.filter(
    (a) => a.bestBand === 'low' && !visibleBands.has('low'),
  ).length;

  return (
    <div style={panelStyle} data-testid="blindspots-panel">
      <h3 style={headerStyle} data-testid="blindspots-panel-header">
        Blindspots — interpreted
      </h3>
      {visible.length === 0 ? (
        <p style={emptyStyle} data-testid="blindspots-empty">
          No high- or medium-confidence blindspots in this trace.
        </p>
      ) : (
        visible.map((a) => (
          <BlindspotInterpretation
            key={a.classKey}
            driveId={a.driveId}
            register={a.register ?? undefined}
            confidence={a.bestConfidence}
            evidenceSources={a.evidenceSources}
          />
        ))
      )}
      {hiddenLow > 0 ? (
        <button
          type="button"
          style={expandButtonStyle}
          onClick={() => setExpanded(true)}
          data-testid="blindspots-expand-low"
        >
          Show low-confidence ({hiddenLow} hidden)
        </button>
      ) : null}
      {expanded && aggregated.some((a) => a.bestBand === 'low') ? (
        <button
          type="button"
          style={expandButtonStyle}
          onClick={() => setExpanded(false)}
          data-testid="blindspots-collapse-low"
        >
          Hide low-confidence
        </button>
      ) : null}
    </div>
  );
}
