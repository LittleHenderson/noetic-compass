import { useEffect, useState } from 'react';
import { apiFetch } from '../../api/client';
import {
  DiagramPreview,
  highlightSyntax,
  type CasDiagram,
} from '../../pages/CompilerPage';

export interface Idea {
  id: string;
  text: string;
  cas_expression: string | null;
  cas_english?: string | null;
  created_at: string;
  compile_error?: string | null;
  ast?: unknown;
  ast_json?: unknown;
}

export interface NodeDetailPanelProps {
  idea: Idea | null;
  onClose: () => void;
  onInvertClicked?: (idea: Idea) => void;
  onDeleteClicked?: (idea: Idea) => void;
}

interface CompileDiagramResponse {
  valid: boolean;
  error?: string | null;
  result?: Record<string, unknown> | null;
  diagram?: CasDiagram | null;
}

function formatTimestamp(iso: string): string {
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso;
    return d.toLocaleString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return iso;
  }
}

export function NodeDetailPanel({
  idea,
  onClose,
  onInvertClicked,
  onDeleteClicked,
}: NodeDetailPanelProps) {
  // Track open state separately so we can animate the slide-in transition
  // even on the very first render. We start "closed" and flip on next tick.
  const [open, setOpen] = useState(false);
  const [diagramResult, setDiagramResult] = useState<CompileDiagramResponse | null>(null);
  const [diagramLoading, setDiagramLoading] = useState(false);
  const [diagramError, setDiagramError] = useState<string | null>(null);

  useEffect(() => {
    if (idea) {
      // schedule open on next frame so the transition runs
      const id = requestAnimationFrame(() => setOpen(true));
      return () => cancelAnimationFrame(id);
    } else {
      setOpen(false);
    }
  }, [idea?.id, idea]);

  useEffect(() => {
    if (!idea?.cas_expression || idea.compile_error) {
      setDiagramResult(null);
      setDiagramError(null);
      setDiagramLoading(false);
      return;
    }

    let cancelled = false;
    setDiagramLoading(true);
    setDiagramError(null);
    setDiagramResult(null);

    (async () => {
      try {
        const result = await apiFetch<CompileDiagramResponse>('/notation/compile', {
          method: 'POST',
          body: JSON.stringify({ expression: idea.cas_expression }),
        });
        if (!cancelled) setDiagramResult(result);
      } catch (err) {
        if (!cancelled) {
          setDiagramError(err instanceof Error ? err.message : String(err));
        }
      } finally {
        if (!cancelled) setDiagramLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [idea?.id, idea?.cas_expression, idea?.compile_error]);

  const handleDelete = () => {
    if (!idea || !onDeleteClicked) return;
    onDeleteClicked(idea);
  };

  // Render the panel at all times when idea is non-null; visibility is driven
  // by the translate-x class so the slide-in works.
  if (!idea) return null;

  const astPayload = idea.ast ?? idea.ast_json;

  return (
    <div
      className={`fixed top-0 right-0 z-40 h-full w-[360px] max-w-[90vw] transform border-l border-white/[0.06] bg-[#0d1117] shadow-2xl transition-transform duration-200 ease-out ${
        open ? 'translate-x-0' : 'translate-x-full'
      }`}
      role="complementary"
      aria-label="Idea details"
    >
      <div className="flex h-full flex-col">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-white/[0.06] px-4 py-3">
          <h2 className="text-accent-teal font-mono text-sm font-semibold">
            Idea details
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded px-2 py-1 font-mono text-xs text-slate-400 hover:bg-white/[0.04] hover:text-slate-200"
            aria-label="Close panel"
          >
            ✕
          </button>
        </div>

        {/* Body — scrollable */}
        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
          {/* Original text */}
          <section>
            <p className="text-[10px] uppercase tracking-wider text-slate-500 font-mono mb-1">
              Original
            </p>
            <p className="text-slate-200 text-sm font-sans leading-relaxed whitespace-pre-wrap">
              {idea.text}
            </p>
          </section>

          {/* CAS expression */}
          <section>
            <p className="text-[10px] uppercase tracking-wider text-slate-500 font-mono mb-1">
              CAS expression
            </p>
            {idea.compile_error ? (
              <div className="rounded border border-red-500/20 bg-red-500/[0.05] p-2">
                <p className="text-red-400 text-[11px] font-mono whitespace-pre-wrap">
                  {idea.compile_error}
                </p>
              </div>
            ) : idea.cas_expression ? (
              <p className="text-accent-teal text-sm font-mono leading-relaxed">
                {highlightSyntax(idea.cas_expression)}
              </p>
            ) : (
              <p className="text-slate-600 text-xs italic">
                (no CAS expression)
              </p>
            )}
            {idea.cas_english && (
              <p className="mt-2 text-[11px] text-slate-500 font-sans leading-relaxed">
                {idea.cas_english}
              </p>
            )}
          </section>

          {/* Captured timestamp */}
          <section>
            <p className="text-[10px] uppercase tracking-wider text-slate-500 font-mono mb-1">
              Captured
            </p>
            <p className="text-slate-400 text-xs font-mono">
              {formatTimestamp(idea.created_at)}
            </p>
          </section>

          {/* Compiler-level structure diagram */}
          {idea.cas_expression && !idea.compile_error && (
            <section>
              <div className="mb-2">
                <p className="text-[10px] uppercase tracking-wider text-slate-500 font-mono">
                  CAS Structure
                </p>
                <p className="mt-1 text-[11px] text-slate-500 font-sans leading-relaxed">
                  Internal compiler diagram for this expression. The graph view
                  shows relationships between ideas; this shows the structure
                  inside this one idea.
                </p>
              </div>
              {diagramLoading && (
                <div className="rounded border border-cyan-500/15 bg-cyan-500/[0.04] p-3 text-[11px] text-cyan-300 font-mono animate-pulse">
                  Building CAS structure diagram...
                </div>
              )}
              {!diagramLoading && diagramError && (
                <div className="rounded border border-red-500/20 bg-red-500/[0.05] p-3 text-[11px] text-red-300 font-mono">
                  {diagramError}
                </div>
              )}
              {!diagramLoading && !diagramError && diagramResult?.diagram && (
                <DiagramPreview
                  diagram={diagramResult.diagram}
                  result={diagramResult.result ?? null}
                />
              )}
            </section>
          )}

          {/* AST */}
          {astPayload !== undefined && astPayload !== null && (
            <section>
              <details className="rounded border border-white/[0.06] bg-white/[0.02]">
                <summary className="cursor-pointer px-3 py-2 font-mono text-[10px] uppercase tracking-wider text-slate-500 hover:text-slate-300">
                  AST
                </summary>
                <pre className="overflow-x-auto px-3 pb-3 text-[10px] font-mono text-slate-400 leading-relaxed">
                  {JSON.stringify(astPayload, null, 2)}
                </pre>
              </details>
            </section>
          )}
        </div>

        {/* Footer actions */}
        <div className="border-t border-white/[0.06] px-4 py-3 flex items-center gap-2">
          <button
            type="button"
            onClick={() => onInvertClicked?.(idea)}
            disabled={!onInvertClicked}
            className="flex-1 rounded border border-fuchsia-500/30 bg-fuchsia-500/10 px-3 py-1.5 font-mono text-xs text-fuchsia-300 transition-colors hover:bg-fuchsia-500/20 disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:bg-fuchsia-500/10"
          >
            Invert this idea…
          </button>
          <button
            type="button"
            onClick={handleDelete}
            disabled={!onDeleteClicked}
            className="rounded border border-red-500/30 bg-red-500/[0.05] px-3 py-1.5 font-mono text-xs text-red-400 transition-colors hover:bg-red-500/10 disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:bg-red-500/[0.05]"
          >
            Delete
          </button>
        </div>
      </div>
    </div>
  );
}

export default NodeDetailPanel;
