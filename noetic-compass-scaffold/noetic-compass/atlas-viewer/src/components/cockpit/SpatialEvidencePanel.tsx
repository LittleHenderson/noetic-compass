import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { CSSProperties, KeyboardEvent } from 'react';
import { motion } from 'framer-motion';
import { THEME, SPRING_SNAPPY } from '../../lib/designTokens';
import type {
  EvidenceRef,
  VisualPrimitive,
  VisualPrimitiveKind,
} from '../../lib/visualPrimitives';
import { ATLAS_STATUS_COLORS } from '../../lib/atlasPalette';
import { toEnglish } from '../../lib/colloquialismMap';

export interface SpatialEvidencePanelProps {
  primitives: VisualPrimitive[];
  selectedPrimitiveId?: string;
  onPrimitiveSelect?: (p: VisualPrimitive) => void;
  onOpenEvidence?: (ref: EvidenceRef) => void;
  emptyStateLabel?: string;
}

const KIND_GLYPHS: Record<VisualPrimitiveKind, string> = {
  point: '●',
  box: '▢',
  polyline: '⤳',
  region: '⬢',
};

const KIND_LABELS: Record<VisualPrimitiveKind, string> = {
  point: 'point',
  box: 'box',
  polyline: 'polyline',
  region: 'region',
};

const CAS_AXIS_SWATCH: Record<string, string> = {
  Noetic: '#a855f7',
  Domain: '#3b82f6',
  Drive: '#f97316',
  Register: '#22c55e',
};

function swatchColor(p: VisualPrimitive): string {
  if (p.cas_axis && CAS_AXIS_SWATCH[p.cas_axis]) {
    return CAS_AXIS_SWATCH[p.cas_axis];
  }
  return ATLAS_STATUS_COLORS.unavailable;
}

function confidenceBadgeColor(confidence: number): string {
  if (confidence > 0.8) return ATLAS_STATUS_COLORS.accepted;
  if (confidence >= 0.5) return ATLAS_STATUS_COLORS.caveat;
  return ATLAS_STATUS_COLORS.constrain;
}

function englishFor(p: VisualPrimitive): string {
  if (p.explanation && p.explanation.length > 0) return p.explanation;
  if (p.cas_label) {
    const parsed = toEnglish(p.cas_label);
    if (parsed.length > 0) return parsed;
  }
  return '';
}

const panelStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 8,
  padding: 12,
  fontFamily: 'system-ui, -apple-system, "Segoe UI", sans-serif',
  fontSize: 13,
  color: '#e5e7eb',
  minWidth: 280,
};

const emptyStyle: CSSProperties = {
  padding: 16,
  textAlign: 'center',
  color: ATLAS_STATUS_COLORS.unavailable,
  fontStyle: 'italic',
};

function cardStyle(selected: boolean): CSSProperties {
  return {
    display: 'flex',
    flexDirection: 'column',
    gap: 4,
    padding: 10,
    // Wave 5.2: no glow halo, no heavy backdrop blur. Selected = subtle
    // teal-tinted background + teal border. Unselected = hairline border.
    background: selected
      ? 'rgba(45, 212, 191, 0.08)'
      : 'rgba(255, 255, 255, 0.02)',
    border: selected
      ? `1px solid ${ATLAS_STATUS_COLORS.activeTrace}`
      : '1px solid rgba(255, 255, 255, 0.06)',
    borderRadius: 6,
    cursor: 'pointer',
    outline: 'none',
    boxShadow: 'none',
    transition: 'border-color 0.15s ease, background 0.15s ease',
  };
}

const headerStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 8,
};

const swatchStyle = (color: string): CSSProperties => ({
  display: 'inline-block',
  width: 10,
  height: 10,
  borderRadius: 2,
  background: color,
  flexShrink: 0,
});

const glyphStyle: CSSProperties = {
  fontSize: 14,
  width: 16,
  textAlign: 'center',
  color: '#cbd5e1',
};

const labelStyle: CSSProperties = {
  flexGrow: 1,
  fontWeight: 600,
  overflow: 'hidden',
  textOverflow: 'ellipsis',
  whiteSpace: 'nowrap',
};

const casLabelStyle: CSSProperties = {
  fontFamily: '"JetBrains Mono", Menlo, Consolas, monospace',
  fontSize: 12,
  color: '#94a3b8',
  wordBreak: 'break-all',
};

const englishStyle: CSSProperties = {
  fontSize: 12,
  color: '#cbd5e1',
};

const footerStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  gap: 6,
  marginTop: 4,
};

function pillStyle(bg: string, fg = '#0f172a'): CSSProperties {
  return {
    display: 'inline-block',
    padding: '2px 8px',
    borderRadius: 999,
    fontSize: 11,
    fontWeight: 600,
    color: fg,
    background: bg,
    backdropFilter: 'blur(8px) saturate(140%)',
    WebkitBackdropFilter: 'blur(8px) saturate(140%)',
  };
}

const evidenceButtonStyle: CSSProperties = {
  padding: '4px 10px',
  fontSize: 11,
  fontWeight: 600,
  letterSpacing: 0.3,
  color: ATLAS_STATUS_COLORS.activeTrace,
  background: 'rgba(45, 212, 191, 0.10)',
  border: `1px solid ${ATLAS_STATUS_COLORS.activeTrace}`,
  borderRadius: 6,
  cursor: 'pointer',
};

export default function SpatialEvidencePanel({
  primitives,
  selectedPrimitiveId,
  onPrimitiveSelect,
  onOpenEvidence,
  emptyStateLabel = 'No spatial evidence for this step',
}: SpatialEvidencePanelProps) {
  const cardRefs = useRef<Array<HTMLDivElement | null>>([]);

  const selectedIndex = useMemo(() => {
    if (!selectedPrimitiveId) return -1;
    return primitives.findIndex((p) => p.id === selectedPrimitiveId);
  }, [primitives, selectedPrimitiveId]);

  const [focusIndex, setFocusIndex] = useState<number>(
    selectedIndex >= 0 ? selectedIndex : 0,
  );

  useEffect(() => {
    if (selectedIndex >= 0) setFocusIndex(selectedIndex);
  }, [selectedIndex]);

  const handleSelect = useCallback(
    (p: VisualPrimitive) => {
      if (onPrimitiveSelect) onPrimitiveSelect(p);
    },
    [onPrimitiveSelect],
  );

  const handleOpenEvidence = useCallback(
    (p: VisualPrimitive) => {
      if (p.evidence_ref && onOpenEvidence) onOpenEvidence(p.evidence_ref);
    },
    [onOpenEvidence],
  );

  const handleKeyDown = useCallback(
    (event: KeyboardEvent<HTMLDivElement>, index: number) => {
      if (primitives.length === 0) return;
      if (event.key === 'ArrowDown') {
        event.preventDefault();
        const next = Math.min(primitives.length - 1, index + 1);
        setFocusIndex(next);
        cardRefs.current[next]?.focus();
        handleSelect(primitives[next]);
      } else if (event.key === 'ArrowUp') {
        event.preventDefault();
        const next = Math.max(0, index - 1);
        setFocusIndex(next);
        cardRefs.current[next]?.focus();
        handleSelect(primitives[next]);
      } else if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        const p = primitives[index];
        if (p.evidence_ref) handleOpenEvidence(p);
        else handleSelect(p);
      }
    },
    [primitives, handleSelect, handleOpenEvidence],
  );

  if (primitives.length === 0) {
    return (
      <section
        aria-label="Spatial Evidence Layer"
        style={panelStyle}
        data-testid="spatial-evidence-panel"
      >
        <div role="status" style={emptyStyle} data-testid="spatial-evidence-empty">
          {emptyStateLabel}
        </div>
      </section>
    );
  }

  return (
    <section
      aria-label="Spatial Evidence Layer"
      style={panelStyle}
      data-testid="spatial-evidence-panel"
    >
      <div role="list" aria-label="Visual primitives">
        {primitives.map((p, index) => {
          const isSelected = p.id === selectedPrimitiveId;
          const isFocus = index === focusIndex;
          const english = englishFor(p);
          const swatch = swatchColor(p);
          const glyph = KIND_GLYPHS[p.kind];
          const kindName = KIND_LABELS[p.kind];
          return (
            <motion.div
              key={p.id}
              ref={(el: HTMLDivElement | null) => {
                cardRefs.current[index] = el;
              }}
              role="listitem"
              aria-selected={isSelected}
              aria-label={`${p.label ?? 'Unnamed primitive'} (${kindName})`}
              data-testid={`spatial-evidence-card-${p.id}`}
              data-selected={isSelected ? 'true' : 'false'}
              tabIndex={isFocus ? 0 : -1}
              style={cardStyle(isSelected)}
              onClick={() => handleSelect(p)}
              onKeyDown={(e: KeyboardEvent<HTMLDivElement>) =>
                handleKeyDown(e, index)
              }
              whileHover={{
                borderColor: isSelected
                  ? ATLAS_STATUS_COLORS.activeTrace
                  : 'rgba(255, 255, 255, 0.12)',
              }}
              whileTap={{ scale: 0.99 }}
              transition={SPRING_SNAPPY}
            >
              <div style={headerStyle}>
                <span
                  aria-hidden="true"
                  style={swatchStyle(swatch)}
                  data-testid={`spatial-evidence-swatch-${p.id}`}
                />
                <span aria-hidden="true" style={glyphStyle} title={kindName}>
                  {glyph}
                </span>
                <span style={labelStyle}>{p.label ?? 'Unnamed primitive'}</span>
              </div>

              {p.cas_label ? (
                <div
                  style={casLabelStyle}
                  data-testid={`spatial-evidence-cas-${p.id}`}
                >
                  {p.cas_label}
                </div>
              ) : null}

              {english ? (
                <div
                  style={englishStyle}
                  data-testid={`spatial-evidence-en-${p.id}`}
                >
                  {english}
                </div>
              ) : null}

              <div style={footerStyle}>
                {typeof p.confidence === 'number' ? (
                  <span
                    data-testid={`spatial-evidence-confidence-${p.id}`}
                    style={pillStyle(confidenceBadgeColor(p.confidence))}
                  >
                    {`conf ${p.confidence.toFixed(2)}`}
                  </span>
                ) : (
                  <span />
                )}
                {p.evidence_ref ? (
                  <button
                    type="button"
                    data-testid={`spatial-evidence-open-${p.id}`}
                    style={evidenceButtonStyle}
                    onClick={(e) => {
                      e.stopPropagation();
                      handleOpenEvidence(p);
                    }}
                  >
                    Open evidence
                  </button>
                ) : null}
              </div>
            </motion.div>
          );
        })}
      </div>
    </section>
  );
}

void THEME;
