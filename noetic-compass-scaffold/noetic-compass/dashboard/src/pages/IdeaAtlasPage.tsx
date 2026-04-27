import { useState, useRef, useEffect, useCallback } from 'react';
import { apiFetch, ApiError } from '../api/client';
import { highlightSyntax } from './CompilerPage';

// ── Types ──

interface Idea {
  id: string;
  text: string;
  cas_expression: string | null;
  cas_english?: string | null;
  created_at: string; // ISO timestamp
  compile_error?: string | null;
}

interface CaptureResponse {
  idea: Idea;
}

interface ListResponse {
  ideas: Idea[];
}

// ── Backend availability state ──
type BackendState = 'available' | 'unavailable' | 'unknown';

function isBackendMissingError(err: unknown): boolean {
  if (err instanceof ApiError) {
    // 404 = endpoint not yet deployed; 503 = service unavailable;
    // 0 = network failure (apiFetch maps fetch failures to status 0)
    return err.status === 404 || err.status === 503 || err.status === 0;
  }
  return false;
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

export function IdeaAtlasPage() {
  const [ideas, setIdeas] = useState<Idea[]>([]);
  const [input, setInput] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [loadingList, setLoadingList] = useState(true);
  const [backendState, setBackendState] = useState<BackendState>('unknown');
  const [error, setError] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea like CompilerPage
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = Math.min(Math.max(el.scrollHeight, 56), 240) + 'px';
  }, [input]);

  // Load existing ideas on mount
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await apiFetch<ListResponse>('/idea_atlas/ideas');
        if (cancelled) return;
        setIdeas(Array.isArray(data.ideas) ? data.ideas : []);
        setBackendState('available');
      } catch (err) {
        if (cancelled) return;
        if (isBackendMissingError(err)) {
          setBackendState('unavailable');
        } else {
          // Some other error (e.g. 500) — surface but don't block UI
          const detail = err instanceof Error ? err.message : String(err);
          setError(detail);
          setBackendState('available');
        }
      } finally {
        if (!cancelled) setLoadingList(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const handleSubmit = useCallback(async () => {
    const trimmed = input.trim();
    if (!trimmed || submitting) return;

    setError(null);
    setSubmitting(true);

    // Optimistic placeholder so user sees the "Translating..." state inline
    const placeholderId = `pending-${Date.now()}`;
    const placeholder: Idea = {
      id: placeholderId,
      text: trimmed,
      cas_expression: null,
      created_at: new Date().toISOString(),
    };
    setIdeas((prev) => [placeholder, ...prev]);
    setInput('');

    try {
      const data = await apiFetch<CaptureResponse>('/idea_atlas/ideas', {
        method: 'POST',
        body: JSON.stringify({ text: trimmed }),
      });
      // Replace placeholder with real idea
      setIdeas((prev) =>
        prev.map((it) => (it.id === placeholderId ? data.idea : it)),
      );
      setBackendState('available');
    } catch (err) {
      if (isBackendMissingError(err)) {
        // Roll the optimistic insert back; show backend-unavailable banner
        setIdeas((prev) => prev.filter((it) => it.id !== placeholderId));
        setBackendState('unavailable');
        // Restore the input so the user doesn't lose their typing
        setInput(trimmed);
      } else {
        const detail = err instanceof Error ? err.message : String(err);
        // Keep the placeholder in the list but mark it as a compile error so
        // the failure renders inline next to the original text.
        setIdeas((prev) =>
          prev.map((it) =>
            it.id === placeholderId
              ? { ...it, compile_error: detail }
              : it,
          ),
        );
      }
    } finally {
      setSubmitting(false);
    }
  }, [input, submitting]);

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  }

  const isPending = (it: Idea) =>
    it.id.startsWith('pending-') &&
    !it.cas_expression &&
    !it.compile_error;

  return (
    <div
      className="flex h-full max-h-[calc(100vh-5rem)] flex-col"
      style={{ backgroundColor: '#0d1117' }}
    >
      {/* Header */}
      <div className="border-b border-white/[0.06] px-6 py-4">
        <h1 className="text-accent-teal font-mono text-lg font-semibold">
          Idea Atlas
        </h1>
        <p className="text-slate-500 text-xs mt-1 font-sans">
          Personal cognitive map. Capture ideas; see their CAS structure.
        </p>
      </div>

      {/* Capture area */}
      <div className="border-b border-white/[0.06] px-6 py-4">
        <div className="flex items-start gap-2">
          <span className="font-mono text-sm font-bold shrink-0 pt-2 text-accent-teal">
            idea&gt;
          </span>
          <div className="flex-1 min-h-[44px]">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Describe an idea, belief, or pattern you want to map..."
              rows={2}
              className="w-full resize-none rounded border border-white/[0.06] bg-black/30 px-3 py-2 font-mono text-sm text-slate-200 placeholder:text-slate-600 focus:border-accent-teal/50 focus:outline-none"
              style={{ minHeight: '56px', maxHeight: '240px' }}
              disabled={backendState === 'unavailable'}
            />
            <div className="mt-2 flex items-center justify-between gap-3">
              <span className="text-[10px] text-slate-600 font-mono">
                Enter to capture, Shift+Enter for newline
              </span>
              <button
                type="button"
                onClick={handleSubmit}
                disabled={
                  !input.trim() ||
                  submitting ||
                  backendState === 'unavailable'
                }
                className="rounded border border-accent-teal/30 bg-accent-teal/10 px-3 py-1.5 font-mono text-xs text-accent-teal transition-colors hover:bg-accent-teal/20 disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:bg-accent-teal/10"
              >
                {submitting ? 'Capturing...' : 'Capture'}
              </button>
            </div>
          </div>
        </div>

        {error && (
          <div className="mt-3 rounded border border-red-500/20 bg-red-500/[0.05] p-2 font-mono text-[11px] text-red-400">
            {error}
          </div>
        )}
      </div>

      {/* List area */}
      <div className="flex-1 overflow-y-auto px-6 py-4">
        {/* Backend-unavailable empty state — distinct from no-ideas-yet state */}
        {backendState === 'unavailable' && (
          <div className="rounded-lg border border-amber-500/20 bg-amber-500/[0.04] p-6 text-center">
            <p className="text-amber-400 font-mono text-sm">
              Backend not yet available
            </p>
            <p className="text-slate-500 text-xs mt-2 font-sans">
              The Idea Atlas API endpoint hasn&apos;t been deployed yet.
              Captured ideas will be saved once the backend comes online.
            </p>
          </div>
        )}

        {/* Loading initial list */}
        {backendState !== 'unavailable' && loadingList && ideas.length === 0 && (
          <div className="text-slate-500 font-mono text-xs animate-pulse">
            Loading atlas...
          </div>
        )}

        {/* Empty state — backend is up but no ideas yet */}
        {backendState !== 'unavailable' &&
          !loadingList &&
          ideas.length === 0 && (
            <div className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-6 text-center">
              <p className="text-slate-400 font-mono text-sm">
                No ideas captured yet.
              </p>
              <p className="text-slate-600 text-xs mt-1 font-sans">
                Type something above to start your atlas.
              </p>
            </div>
          )}

        {/* List of ideas */}
        {ideas.length > 0 && (
          <div className="space-y-3">
            {ideas.map((idea) => (
              <div
                key={idea.id}
                className={`animate-[fadeSlideIn_0.25s_ease-out] rounded-lg border p-4 font-mono text-xs ${
                  idea.compile_error
                    ? 'border-red-500/20 bg-red-500/[0.03]'
                    : isPending(idea)
                      ? 'border-white/[0.06] bg-white/[0.02]'
                      : 'border-emerald-500/15 bg-emerald-500/[0.02]'
                }`}
              >
                {/* Original text — small, dim */}
                <p className="text-[11px] text-slate-500 font-sans leading-relaxed mb-2 whitespace-pre-wrap">
                  {idea.text}
                </p>

                {/* CAS expression / loading / error */}
                {isPending(idea) ? (
                  <p className="text-slate-500 text-[12px] animate-pulse">
                    Translating to CAS notation...
                  </p>
                ) : idea.compile_error ? (
                  <div className="rounded border border-red-500/20 bg-red-500/[0.05] p-2">
                    <p className="text-red-400 text-[11px] whitespace-pre-wrap">
                      {idea.compile_error}
                    </p>
                  </div>
                ) : idea.cas_expression ? (
                  <div>
                    <p className="text-accent-teal text-[13px] leading-relaxed">
                      {highlightSyntax(idea.cas_expression)}
                    </p>
                    {idea.cas_english && (
                      <p className="text-[10px] text-slate-500 font-sans mt-1">
                        {idea.cas_english}
                      </p>
                    )}
                  </div>
                ) : (
                  <p className="text-slate-600 text-[11px] italic">
                    (no CAS expression returned)
                  </p>
                )}

                {/* Meta line */}
                <p className="mt-2 text-[9px] uppercase tracking-wider text-slate-600">
                  {formatTimestamp(idea.created_at)}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
