import { useMemo, useState, type CSSProperties } from 'react';
import { GlassPanel } from '../components/ui/GlassPanel';
import PageShell from '../components/ui/PageShell';
import {
  ACCENT_CYAN,
  ACCENT_TEAL,
  COLORS,
  FONT_MONO,
  THEME,
} from '../lib/designTokens';
import {
  LSA_STORAGE_KEY,
  lsaCalibration20,
  type LsaCalibrationItem,
  type LsaDefinition,
} from '../fixtures/lsaCalibration20';

type Confidence = '1' | '2' | '3' | '4' | '5' | '';

interface LsaRating {
  label: string;
  confidence: Confidence;
  notes: string;
  updatedAt?: string;
}

type LsaRatingMap = Record<string, LsaRating>;

const EMPTY_RATING: LsaRating = {
  label: '',
  confidence: '',
  notes: '',
};

const confidenceOptions: Array<{ value: Confidence; label: string; meaning: string }> = [
  { value: '1', label: '1', meaning: 'Guessing' },
  { value: '2', label: '2', meaning: 'Weak' },
  { value: '3', label: '3', meaning: 'Possible' },
  { value: '4', label: '4', meaning: 'Sure' },
  { value: '5', label: '5', meaning: 'Very sure' },
];

const instructionSteps = [
  'Read options A and B.',
  'Rate only the option named in teal.',
  'Choose the label that describes that option.',
  'Mark how sure you are.',
  'Click Save & Next, then export at the end.',
];

function loadRatings(): LsaRatingMap {
  if (typeof window === 'undefined') {
    return {};
  }

  try {
    const raw = window.localStorage.getItem(LSA_STORAGE_KEY);
    if (!raw) {
      return {};
    }
    const parsed = JSON.parse(raw) as LsaRatingMap;
    return parsed && typeof parsed === 'object' ? parsed : {};
  } catch {
    return {};
  }
}

function saveRatings(ratings: LsaRatingMap) {
  if (typeof window === 'undefined') {
    return;
  }
  window.localStorage.setItem(LSA_STORAGE_KEY, JSON.stringify(ratings));
}

function downloadFile(name: string, contents: string, type: string) {
  const blob = new Blob([contents], { type });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = name;
  anchor.click();
  URL.revokeObjectURL(url);
}

function toCsv(rows: Array<Record<string, string>>) {
  const headers = ['item_id', 'axis', 'selected_label', 'confidence', 'notes'];
  const escape = (value: string) => `"${value.replace(/"/g, '""')}"`;
  return [
    headers.join(','),
    ...rows.map((row) => headers.map((header) => escape(row[header] ?? '')).join(',')),
  ].join('\n');
}

function ratingComplete(rating: LsaRating | undefined) {
  return Boolean(rating?.label && rating?.confidence);
}

const pageGridStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 320px), 1fr))',
  gap: 18,
  alignItems: 'start',
};

const stackStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 14,
};

const instructionGridStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 180px), 1fr))',
  gap: 10,
};

const smallLabelStyle: CSSProperties = {
  fontSize: 11,
  letterSpacing: 1.3,
  textTransform: 'uppercase',
  color: COLORS.textMuted,
  fontWeight: 700,
};

const primaryButtonStyle: CSSProperties = {
  minHeight: 38,
  border: '1px solid rgba(45, 212, 191, 0.36)',
  borderRadius: 6,
  background: 'rgba(45, 212, 191, 0.12)',
  color: '#ccfbf1',
  fontFamily: THEME.fontFamily,
  fontWeight: 700,
  cursor: 'pointer',
};

const secondaryButtonStyle: CSSProperties = {
  minHeight: 36,
  border: '1px solid rgba(255, 255, 255, 0.10)',
  borderRadius: 6,
  background: 'rgba(255, 255, 255, 0.04)',
  color: COLORS.textPrimary,
  fontFamily: THEME.fontFamily,
  fontWeight: 650,
  cursor: 'pointer',
};

function axisName(axis: LsaCalibrationItem['axis']) {
  return axis === '40e' ? '40 Elements' : '28 Foundations';
}

function focusedOption(itemText: string) {
  const match = itemText.match(/Focus: ([AB])\.$/);
  return match?.[1] ?? 'A';
}

function itemTextWithoutFocus(itemText: string) {
  return itemText.replace(/\s*Focus: [AB]\.$/, '.');
}

function definitionText(definition: LsaDefinition | undefined) {
  return definition?.definition ?? 'Choose the label that describes the option you are rating.';
}

export default function LsaCalibrationPage() {
  const [ratings, setRatings] = useState<LsaRatingMap>(() => loadRatings());
  const [index, setIndex] = useState(0);
  const [raterId, setRaterId] = useState('');
  const [filter, setFilter] = useState('');

  const item = lsaCalibration20.items[index];
  const focus = focusedOption(item.text);
  const otherOption = focus === 'A' ? 'B' : 'A';
  const definitions = lsaCalibration20.definitions[item.axis];
  const rating = ratings[item.id] ?? EMPTY_RATING;
  const selectedDefinition = definitions.find((definition) => definition.label === rating.label);
  const completeCount = lsaCalibration20.items.filter((candidate) =>
    ratingComplete(ratings[candidate.id]),
  ).length;
  const progressPercent = Math.round((completeCount / lsaCalibration20.items.length) * 100);

  const filteredDefinitions = useMemo(() => {
    const normalized = filter.trim().toLowerCase();
    if (!normalized) {
      return definitions;
    }
    return definitions.filter((definition) =>
      `${definition.label} ${definition.definition}`.toLowerCase().includes(normalized),
    );
  }, [definitions, filter]);

  const exportRows = useMemo(
    () =>
      lsaCalibration20.items.map((candidate) => ({
        item_id: candidate.id,
        axis: candidate.axis,
        selected_label: ratings[candidate.id]?.label ?? '',
        confidence: ratings[candidate.id]?.confidence ?? '',
        notes: ratings[candidate.id]?.notes ?? '',
      })),
    [ratings],
  );

  function updateRating(patch: Partial<LsaRating>) {
    const next = {
      ...ratings,
      [item.id]: {
        ...EMPTY_RATING,
        ...rating,
        ...patch,
        updatedAt: new Date().toISOString(),
      },
    };
    setRatings(next);
    saveRatings(next);
  }

  function goTo(nextIndex: number) {
    setFilter('');
    setIndex(Math.max(0, Math.min(lsaCalibration20.items.length - 1, nextIndex)));
  }

  function exportJson() {
    const payload = {
      schema: 'cas_harness_lsa_calibration_ratings.v0_1',
      sourceSchema: lsaCalibration20.schema,
      status: 'human_rater_calibration_only',
      raterId,
      completed: completeCount,
      total: lsaCalibration20.items.length,
      exportedAt: new Date().toISOString(),
      rows: exportRows,
    };
    downloadFile('lsa-calibration-20-ratings.json', JSON.stringify(payload, null, 2), 'application/json');
  }

  function exportCsv() {
    downloadFile('lsa-calibration-20-ratings.csv', toCsv(exportRows), 'text/csv');
  }

  return (
    <PageShell cardMaxWidth={1120} contentAlign="start">
      <div style={stackStyle}>
        <header style={{ display: 'flex', justifyContent: 'space-between', gap: 18, flexWrap: 'wrap' }}>
          <div>
            <div style={smallLabelStyle}>LSA calibration</div>
            <h1 style={{ margin: '6px 0 8px', fontSize: 30, letterSpacing: 0, lineHeight: 1.08 }}>
              Human meaning check
            </h1>
            <p style={{ margin: 0, maxWidth: 720, color: COLORS.textSecondary, fontSize: 14, lineHeight: 1.55 }}>
              Twenty stripped items. Rate only the named option, choose its meaning label, then export.
            </p>
          </div>
          <GlassPanel intensity="thin" padding="10px 12px" style={{ minWidth: 180 }}>
            <div style={smallLabelStyle}>Progress</div>
            <div style={{ marginTop: 8, display: 'flex', justifyContent: 'space-between', color: COLORS.textPrimary }}>
              <strong>{completeCount}/20</strong>
              <span>{progressPercent}%</span>
            </div>
            <div
              aria-hidden="true"
              style={{
                marginTop: 10,
                height: 6,
                borderRadius: 999,
                overflow: 'hidden',
                background: 'rgba(255,255,255,0.08)',
              }}
            >
              <div
                style={{
                  width: `${progressPercent}%`,
                  height: '100%',
                  background: `linear-gradient(90deg, ${ACCENT_TEAL}, ${ACCENT_CYAN})`,
                }}
              />
            </div>
          </GlassPanel>
        </header>

        <GlassPanel intensity="thin" padding={14} as="section" ariaLabel="Start here instructions">
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 14, flexWrap: 'wrap' }}>
            <div>
              <div style={smallLabelStyle}>Start here</div>
              <p style={{ margin: '6px 0 0', color: COLORS.textSecondary, fontSize: 13, lineHeight: 1.45 }}>
                Work left to right. Your choices save on this device as you go.
              </p>
            </div>
            <span
              style={{
                alignSelf: 'flex-start',
                border: '1px solid rgba(255,255,255,0.10)',
                borderRadius: 999,
                color: COLORS.textSecondary,
                fontSize: 12,
                padding: '5px 10px',
              }}
            >
              No hidden answer key
            </span>
          </div>
          <ol style={{ ...instructionGridStyle, margin: '12px 0 0', padding: 0, listStyle: 'none' }}>
            {instructionSteps.map((step, stepIndex) => (
              <li
                key={step}
                style={{
                  display: 'flex',
                  gap: 10,
                  alignItems: 'flex-start',
                  padding: '10px 11px',
                  border: '1px solid rgba(255,255,255,0.07)',
                  borderRadius: 8,
                  background: 'rgba(255,255,255,0.025)',
                  color: COLORS.textSecondary,
                  fontSize: 13,
                  lineHeight: 1.35,
                }}
              >
                <span
                  style={{
                    display: 'inline-grid',
                    placeItems: 'center',
                    flex: '0 0 22px',
                    width: 22,
                    height: 22,
                    borderRadius: 999,
                    background: 'rgba(45, 212, 191, 0.13)',
                    color: '#99f6e4',
                    fontWeight: 800,
                  }}
                >
                  {stepIndex + 1}
                </span>
                <span>{step}</span>
              </li>
            ))}
          </ol>
        </GlassPanel>

        <div style={pageGridStyle}>
          <section style={stackStyle}>
            <GlassPanel intensity="regular" padding={18} as="section" ariaLabel="Current item">
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
                <div>
                  <div style={smallLabelStyle}>Item {index + 1} of 20</div>
                  <div style={{ marginTop: 6, fontFamily: FONT_MONO, color: ACCENT_TEAL, fontSize: 12 }}>
                    {item.id}
                  </div>
                </div>
                <span
                  style={{
                    alignSelf: 'flex-start',
                    border: '1px solid rgba(45, 212, 191, 0.24)',
                    borderRadius: 999,
                    padding: '5px 9px',
                    color: '#99f6e4',
                    fontSize: 12,
                    fontWeight: 700,
                  }}
                >
                  {axisName(item.axis)}
                </span>
              </div>
              <p
                style={{
                  margin: '18px 0 0',
                  color: COLORS.textPrimary,
                  fontSize: 18,
                  lineHeight: 1.62,
                }}
              >
                {itemTextWithoutFocus(item.text)}
              </p>
              <div
                style={{
                  marginTop: 16,
                  padding: '12px 14px',
                  borderRadius: 8,
                  border: '1px solid rgba(45, 212, 191, 0.32)',
                  background: 'rgba(45, 212, 191, 0.10)',
                  color: '#ccfbf1',
                  fontWeight: 800,
                  lineHeight: 1.45,
                }}
              >
                Rate option {focus} only. Do not label option {otherOption}.
                <span style={{ display: 'block', marginTop: 4, color: '#99f6e4', fontWeight: 600 }}>
                  Option {otherOption} is only there to help you tell the two meanings apart.
                </span>
              </div>
            </GlassPanel>

            <GlassPanel intensity="thin" padding={16} as="section" ariaLabel="Rater controls">
              <div style={stackStyle}>
                <label style={stackStyle}>
                  <span style={smallLabelStyle}>Rater ID</span>
                  <input
                    value={raterId}
                    onChange={(event) => setRaterId(event.target.value)}
                    placeholder="Name or initials"
                    style={{
                      minHeight: 40,
                      border: '1px solid rgba(255,255,255,0.12)',
                      borderRadius: 6,
                      background: 'rgba(2, 6, 23, 0.64)',
                      color: COLORS.textPrimary,
                      padding: '0 12px',
                      fontFamily: THEME.fontFamily,
                    }}
                  />
                </label>

                <label style={stackStyle}>
                  <span style={smallLabelStyle}>Chosen label</span>
                  <p style={{ margin: '-4px 0 0', color: COLORS.textSecondary, fontSize: 13, lineHeight: 1.45 }}>
                    Pick the label that describes option {focus}. Do not label the whole item.
                  </p>
                  <select
                    value={rating.label}
                    onChange={(event) => updateRating({ label: event.target.value })}
                    style={{
                      minHeight: 42,
                      border: '1px solid rgba(255,255,255,0.12)',
                      borderRadius: 6,
                      background: '#06111f',
                      color: COLORS.textPrimary,
                      padding: '0 12px',
                      fontFamily: THEME.fontFamily,
                    }}
                  >
                    <option value="">Select a label</option>
                    {definitions.map((definition) => (
                      <option key={definition.label} value={definition.label}>
                        {definition.label} — {definition.definition}
                      </option>
                    ))}
                  </select>
                </label>

                <div>
                  <div style={smallLabelStyle}>Confidence</div>
                  <p style={{ margin: '6px 0 0', color: COLORS.textSecondary, fontSize: 13, lineHeight: 1.45 }}>
                    Confidence means how sure you are that your chosen label describes option {focus}.
                  </p>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 8, marginTop: 8 }}>
                    {confidenceOptions.map((option) => {
                      const active = rating.confidence === option.value;
                      return (
                        <button
                          key={option.value}
                          type="button"
                          onClick={() => updateRating({ confidence: option.value })}
                          style={{
                            ...secondaryButtonStyle,
                            background: active ? 'rgba(45, 212, 191, 0.16)' : secondaryButtonStyle.background,
                            border: active ? '1px solid rgba(45, 212, 191, 0.44)' : secondaryButtonStyle.border,
                            color: active ? '#ccfbf1' : COLORS.textSecondary,
                          }}
                        >
                          <span style={{ display: 'block', fontSize: 15 }}>{option.label}</span>
                          <span style={{ display: 'block', marginTop: 2, fontSize: 10, fontWeight: 650 }}>
                            {option.meaning}
                          </span>
                        </button>
                      );
                    })}
                  </div>
                </div>

                <label style={stackStyle}>
                  <span style={smallLabelStyle}>Notes</span>
                  <textarea
                    value={rating.notes}
                    onChange={(event) => updateRating({ notes: event.target.value })}
                    rows={4}
                    placeholder="Optional"
                    style={{
                      resize: 'vertical',
                      border: '1px solid rgba(255,255,255,0.12)',
                      borderRadius: 6,
                      background: 'rgba(2, 6, 23, 0.64)',
                      color: COLORS.textPrimary,
                      padding: 12,
                      fontFamily: THEME.fontFamily,
                      lineHeight: 1.45,
                    }}
                  />
                </label>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                  <button type="button" onClick={() => goTo(index - 1)} style={secondaryButtonStyle}>
                    Previous
                  </button>
                  <button type="button" onClick={() => goTo(index + 1)} style={primaryButtonStyle}>
                    Save & Next
                  </button>
                </div>
              </div>
            </GlassPanel>
          </section>

          <aside style={stackStyle}>
            <GlassPanel intensity="regular" padding={18} as="section" ariaLabel="Selected definition">
              <div style={smallLabelStyle}>Selected meaning</div>
              <div style={{ marginTop: 10, fontSize: 22, fontWeight: 800, color: '#ccfbf1' }}>
                {rating.label || 'No label selected'}
              </div>
              <p style={{ margin: '10px 0 0', color: COLORS.textSecondary, lineHeight: 1.55 }}>
                {definitionText(selectedDefinition)}
              </p>
            </GlassPanel>

            <GlassPanel intensity="thin" padding={16} as="section" ariaLabel="Definition search">
              <div style={stackStyle}>
                <label style={stackStyle}>
                  <span style={smallLabelStyle}>Definition search</span>
                  <input
                    value={filter}
                    onChange={(event) => setFilter(event.target.value)}
                    placeholder="Filter labels"
                    style={{
                      minHeight: 38,
                      border: '1px solid rgba(255,255,255,0.12)',
                      borderRadius: 6,
                      background: 'rgba(2, 6, 23, 0.64)',
                      color: COLORS.textPrimary,
                      padding: '0 12px',
                      fontFamily: THEME.fontFamily,
                    }}
                  />
                </label>
                <div style={{ maxHeight: 270, overflow: 'auto', paddingRight: 4 }}>
                  {filteredDefinitions.map((definition) => {
                    const active = definition.label === rating.label;
                    return (
                      <button
                        key={definition.label}
                        type="button"
                        onClick={() => updateRating({ label: definition.label })}
                        style={{
                          width: '100%',
                          textAlign: 'left',
                          border: active
                            ? '1px solid rgba(45, 212, 191, 0.40)'
                            : '1px solid rgba(255, 255, 255, 0.07)',
                          borderRadius: 6,
                          background: active ? 'rgba(45, 212, 191, 0.12)' : 'rgba(255,255,255,0.025)',
                          color: COLORS.textPrimary,
                          padding: '10px 12px',
                          marginBottom: 8,
                          cursor: 'pointer',
                          fontFamily: THEME.fontFamily,
                        }}
                      >
                        <strong style={{ color: active ? '#99f6e4' : COLORS.textPrimary }}>
                          {definition.label}
                        </strong>
                        <span style={{ display: 'block', marginTop: 4, color: COLORS.textSecondary, lineHeight: 1.4 }}>
                          {definition.definition}
                        </span>
                      </button>
                    );
                  })}
                </div>
              </div>
            </GlassPanel>

            <GlassPanel intensity="regular" padding={16} as="section" ariaLabel="Export ratings">
              <div style={smallLabelStyle}>Export</div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginTop: 12 }}>
                <button type="button" onClick={exportJson} style={primaryButtonStyle}>
                  JSON
                </button>
                <button type="button" onClick={exportCsv} style={secondaryButtonStyle}>
                  CSV
                </button>
              </div>
              <p style={{ margin: '12px 0 0', color: COLORS.textMuted, fontSize: 12, lineHeight: 1.45 }}>
                Export after all 20 are complete. Calibration only; this page does not create a claim.
              </p>
            </GlassPanel>
          </aside>
        </div>
      </div>
    </PageShell>
  );
}
