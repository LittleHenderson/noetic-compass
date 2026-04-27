import { useEffect, useState, useCallback } from 'react';
import { apiFetch, ApiError } from '../../api/client';
import { highlightSyntax } from '../../pages/CompilerPage';

// ── Types ──

/**
 * Minimal Idea shape consumed by the modal. The full Idea type lives inside
 * IdeaAtlasPage.tsx (Agent J's territory) — we duplicate the shape here so
 * this component is independent and can be wired up by a follow-up agent
 * without circular imports. The wiring step may swap this for a shared type.
 */
export interface InversionModalIdea {
  id: string;
  text: string;
  cas_expression: string | null;
  cas_english?: string | null;
}

export interface InversionModalProps {
  idea: InversionModalIdea | null;
  onClose: () => void;
  onConfirm: (params: { invertedCas: string; axis: string }) => void;
}

interface InvertResponse {
  original_idea: { id: string; text: string; cas_expression: string | null };
  inverted_cas: string;
  inverted_ast: unknown;
  axis: string;
  axis_description: string;
}

// ── Axis catalog ──

interface AxisDef {
  key: 'N' | 'W' | 'F' | 'E' | 'S' | 'A' | 'P';
  label: string;
  short: string;
  comingSoon: boolean;
}

const AXES: AxisDef[] = [
  { key: 'N', label: 'Operator / Noetic involution (^2↔^3, ^5↔^6, ^8↔^9)', short: 'Noetic', comingSoon: false },
  { key: 'W', label: 'Domain precedence reversal (P↔O, C↔E)', short: 'Domain', comingSoon: false },
  { key: 'F', label: 'Drive pair flip (F1↔F7, F2↔F6, F3↔F5)', short: 'Drive', comingSoon: false },
  { key: 'E', label: 'State-vector entropy (coming soon)', short: 'Entropy', comingSoon: true },
  { key: 'S', label: 'Sub-drive variance (coming soon)', short: 'Sub-drive', comingSoon: true },
  { key: 'A', label: 'Pathway RPM chain (coming soon)', short: 'Pathway', comingSoon: true },
  { key: 'P', label: 'Compound (N + W + F)', short: 'Compound', comingSoon: false },
];

// ── Component ──

export function InversionModal({ idea, onClose, onConfirm }: InversionModalProps) {
  const [selectedAxis, setSelectedAxis] = useState<string | null>(null);
  const [result, setResult] = useState<InvertResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notImplemented, setNotImplemented] = useState(false);

  // Reset state whenever a new idea is opened
  useEffect(() => {
    if (idea) {
      setSelectedAxis(null);
      setResult(null);
      setLoading(false);
      setError(null);
      setNotImplemented(false);
    }
  }, [idea?.id]);

  // Escape-to-close
  useEffect(() => {
    if (!idea) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose();
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [idea, onClose]);

  const pickAxis = useCallback(
    async (axis: AxisDef) => {
      if (!idea || axis.comingSoon) return;
      setSelectedAxis(axis.key);
      setLoading(true);
      setError(null);
      setNotImplemented(false);
      setResult(null);
      try {
        const res = await apiFetch<InvertResponse>('/idea_atlas/invert', {
          method: 'POST',
          body: JSON.stringify({ idea_id: idea.id, axis: axis.key }),
        });
        setResult(res);
      } catch (err) {
        if (err instanceof ApiError) {
          if (err.status === 501) {
            setNotImplemented(true);
          } else if (err.status === 422) {
            setError(`Compiler error: ${err.detail}`);
          } else {
            setError(err.detail || `Inversion failed (HTTP ${err.status}).`);
          }
        } else {
          setError(err instanceof Error ? err.message : String(err));
        }
      } finally {
        setLoading(false);
      }
    },
    [idea],
  );

  const onCommit = useCallback(() => {
    if (!result) return;
    onConfirm({ invertedCas: result.inverted_cas, axis: result.axis });
  }, [result, onConfirm]);

  if (!idea) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4"
      onClick={onClose}
      role="presentation"
    >
      <div
        className="relative w-full max-w-2xl rounded-xl border border-cyan-500/20 bg-dark-800 p-6 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label="Invert idea"
      >
        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-slate-500 hover:text-slate-200 transition-colors"
          aria-label="Close"
        >
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path d="M5 5l10 10M15 5L5 15" strokeLinecap="round" />
          </svg>
        </button>

        {/* Header */}
        <div className="mb-5">
          <h2 className="text-lg font-semibold text-slate-100">Invert Idea</h2>
          <p className="mt-1 text-xs text-slate-400">
            Pick an inversion axis to generate the structural opposite of this idea.
          </p>
        </div>

        {/* Original idea */}
        <div className="mb-5 rounded-lg border border-white/[0.06] bg-white/[0.02] p-3">
          <p className="text-[11px] uppercase tracking-wide text-slate-500 mb-1">Original</p>
          <p className="text-sm text-slate-200">{idea.text}</p>
          {idea.cas_expression && (
            <p className="mt-2 font-mono text-xs">{highlightSyntax(idea.cas_expression)}</p>
          )}
        </div>

        {/* Axis picker */}
        <div className="mb-4">
          <p className="text-[11px] uppercase tracking-wide text-slate-500 mb-2">Inversion Axis</p>
          <div className="flex flex-wrap gap-2">
            {AXES.map((axis) => {
              const isSelected = selectedAxis === axis.key;
              const disabled = axis.comingSoon || loading;
              return (
                <button
                  key={axis.key}
                  onClick={() => pickAxis(axis)}
                  disabled={disabled}
                  title={axis.label}
                  className={[
                    'group relative px-3 py-1.5 rounded-md text-xs font-mono border transition-colors',
                    isSelected
                      ? 'border-cyan-400 bg-cyan-500/15 text-cyan-200'
                      : 'border-white/[0.08] bg-white/[0.02] text-slate-300 hover:border-cyan-500/40 hover:text-slate-100',
                    disabled && !isSelected ? 'opacity-40 cursor-not-allowed hover:border-white/[0.08] hover:text-slate-300' : '',
                  ].join(' ')}
                  aria-pressed={isSelected}
                >
                  <span className="font-bold">{axis.key}</span>
                  <span className="ml-1 text-[10px] text-slate-500">{axis.short}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Result region */}
        <div className="min-h-[120px] rounded-lg border border-white/[0.06] bg-white/[0.02] p-3">
          {loading && (
            <div className="flex items-center gap-2 text-xs text-slate-400">
              <span className="inline-block h-3 w-3 rounded-full border-2 border-cyan-400 border-t-transparent animate-spin" />
              Inverting along axis {selectedAxis}…
            </div>
          )}

          {!loading && notImplemented && (
            <p className="text-xs text-amber-300">
              This axis is not yet implemented (planned for a later sprint).
            </p>
          )}

          {!loading && error && (
            <p className="text-xs text-rose-300">{error}</p>
          )}

          {!loading && !error && !notImplemented && result && (
            <div className="space-y-3">
              <div>
                <p className="text-[10px] uppercase tracking-wide text-slate-500 mb-1">Original CAS</p>
                <p className="font-mono text-xs text-slate-400">
                  {idea.cas_expression ? highlightSyntax(idea.cas_expression) : <span className="italic">none</span>}
                </p>
              </div>
              <div>
                <p className="text-[10px] uppercase tracking-wide text-slate-500 mb-1">Inverted CAS</p>
                <p className="font-mono text-xs">{highlightSyntax(result.inverted_cas)}</p>
              </div>
              <p className="text-[11px] text-slate-400 italic">{result.axis_description}</p>
            </div>
          )}

          {!loading && !error && !notImplemented && !result && !selectedAxis && (
            <p className="text-xs text-slate-500">Select an axis above to preview the inversion.</p>
          )}
        </div>

        {/* Footer actions */}
        <div className="mt-5 flex items-center justify-end gap-2">
          <button
            onClick={onClose}
            className="px-3 py-1.5 rounded-md text-xs border border-white/[0.08] text-slate-300 hover:text-slate-100 hover:border-white/20 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={onCommit}
            disabled={!result || loading}
            className={[
              'px-3 py-1.5 rounded-md text-xs font-semibold transition-colors',
              !result || loading
                ? 'border border-white/[0.06] bg-white/[0.02] text-slate-500 cursor-not-allowed'
                : 'border border-cyan-400 bg-cyan-500/20 text-cyan-100 hover:bg-cyan-500/30',
            ].join(' ')}
          >
            Commit Inversion
          </button>
        </div>
      </div>
    </div>
  );
}

export default InversionModal;
