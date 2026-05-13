import { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { apiFetch, ApiError } from '../api/client';
import { highlightSyntax } from './CompilerPage';
import { GraphView } from '../components/idea-atlas/GraphView';
import { NodeDetailPanel } from '../components/idea-atlas/NodeDetailPanel';
import { InversionModal } from '../components/idea-atlas/InversionModal';
import { useRippleAnimation } from '../components/idea-atlas/useRippleAnimation';
import { TraceLoader } from '../components/idea-atlas/TraceLoader';
import {
  ThoughtTreeView,
  type ThoughtTreeNode as TreeViewNode,
  type ThoughtTree as TreeViewTree,
} from '../components/idea-atlas/ThoughtTreeView';
import type { AtlasTrace } from '../lib/trace';

// ── Types ──

interface Idea {
  id: string;
  text: string;
  cas_expression: string | null;
  cas_english?: string | null;
  created_at: string; // ISO timestamp
  compile_error?: string | null;
  ast?: unknown;
  ast_json?: unknown;
}

interface AtlasEdge {
  source: string;
  target: string;
  score: number;
  breakdown?: Record<string, number>;
}

type ViewMode = 'list' | 'graph' | 'trace';

// Backend returns flat shapes — Idea on POST, Idea[] on GET — not wrapped.
type CaptureResponse = Idea;
type ListResponse = Idea[];

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

interface SpeechAlternativeLike {
  transcript: string;
}

interface SpeechResultLike {
  readonly length: number;
  readonly isFinal: boolean;
  [index: number]: SpeechAlternativeLike | undefined;
}

interface SpeechResultListLike {
  readonly length: number;
  [index: number]: SpeechResultLike | undefined;
}

interface SpeechRecognitionResultEventLike extends Event {
  resultIndex: number;
  results: SpeechResultListLike;
}

interface SpeechRecognitionErrorEventLike extends Event {
  error?: string;
  message?: string;
}

interface SpeechRecognitionLike {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onstart: (() => void) | null;
  onresult: ((event: SpeechRecognitionResultEventLike) => void) | null;
  onerror: ((event: SpeechRecognitionErrorEventLike) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
  abort: () => void;
}

type SpeechRecognitionConstructor = new () => SpeechRecognitionLike;

function getSpeechRecognitionCtor(): SpeechRecognitionConstructor | null {
  if (typeof window === 'undefined') return null;
  const speechWindow = window as Window & {
    SpeechRecognition?: SpeechRecognitionConstructor;
    webkitSpeechRecognition?: SpeechRecognitionConstructor;
  };
  return speechWindow.SpeechRecognition ?? speechWindow.webkitSpeechRecognition ?? null;
}

export function IdeaAtlasPage() {
  const [ideas, setIdeas] = useState<Idea[]>([]);
  const [input, setInput] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [loadingList, setLoadingList] = useState(true);
  const [backendState, setBackendState] = useState<BackendState>('unknown');
  const [error, setError] = useState<string | null>(null);
  const [speechStatus, setSpeechStatus] = useState<string | null>(null);
  const [listening, setListening] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);
  const speechBaseRef = useRef('');
  const speechSupported = useMemo(() => getSpeechRecognitionCtor() !== null, []);

  // ── Sprint 2 additions: view-mode toggle, graph edges, selected node ──
  const [viewMode, setViewMode] = useState<ViewMode>('list');
  const [edges, setEdges] = useState<AtlasEdge[]>([]);
  const [edgesLoaded, setEdgesLoaded] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [recentIdeaId, setRecentIdeaId] = useState<string | null>(null);
  const { rippleClass } = useRippleAnimation(recentIdeaId);

  // ── Sprint 3 wiring: inversion modal ──
  const [invertingIdea, setInvertingIdea] = useState<Idea | null>(null);

  // ── Atlas v0 wiring: traceability_v0 thought-tree viewer ──
  // The TRACE tab is independent of the Idea backend — it works fully
  // offline against a loaded JSON file. No backend dependency.
  const [loadedTrace, setLoadedTrace] = useState<AtlasTrace | null>(null);
  const [traceError, setTraceError] = useState<string | null>(null);
  const [selectedTraceNodeId, setSelectedTraceNodeId] = useState<string | null>(null);
  const [tracePanelOpen, setTracePanelOpen] = useState(true);
  const selectedNodeSectionRef = useRef<HTMLElement | null>(null);
  const handleTraceLoaded = useCallback((trace: AtlasTrace) => {
    setLoadedTrace(trace);
    setTraceError(null);
    setSelectedTraceNodeId(trace.thought_tree.nodes[0]?.id ?? null);
    setTracePanelOpen(true);
  }, []);
  const handleTraceError = useCallback((message: string) => {
    setTraceError(message);
  }, []);
  const selectedTraceNode: TreeViewNode | null = useMemo(() => {
    if (!loadedTrace || !selectedTraceNodeId) return null;
    return (
      loadedTrace.thought_tree.nodes.find(
        (n) => n.id === selectedTraceNodeId,
      ) ?? null
    );
  }, [loadedTrace, selectedTraceNodeId]);
  // Whenever the selected node changes (via card click), pop the side
  // panel open if it's hidden and scroll the SELECTED NODE section
  // into view. The user feedback (2026-05-13) was that clicks "didn't
  // seem to do anything" — what was happening is the click did select
  // but the detail was below the fold or the panel was collapsed.
  useEffect(() => {
    if (!selectedTraceNodeId) return;
    setTracePanelOpen(true);
    requestAnimationFrame(() => {
      selectedNodeSectionRef.current?.scrollIntoView({
        behavior: 'smooth',
        block: 'nearest',
      });
    });
  }, [selectedTraceNodeId]);

  // Fetch edges lazily — first time the user switches into GRAPH view.
  // Backend exposes GET /idea_atlas/edges?similarity_threshold=0.2; if 404,
  // we fall back to no edges and the graph still renders nodes only.
  useEffect(() => {
    if (viewMode !== 'graph' || edgesLoaded || loadingList) return;
    let cancelled = false;
    (async () => {
      try {
        const data = await apiFetch<AtlasEdge[]>(
          // similarity_threshold is the backend's param name. Default 0.2 —
          // gentle enough to surface domain-only matches (which score ~0.25)
          // so new users see structural connections immediately. Anything
          // below 0.2 is genuine noise.
          '/idea_atlas/edges?similarity_threshold=0.2',
        );
        if (cancelled) return;
        setEdges(Array.isArray(data) ? data : []);
      } catch (err) {
        if (cancelled) return;
        // 404 / 503 / network — backend not yet shipping edges. Render nodes
        // without edges; not an error worth surfacing in the UI.
        if (!isBackendMissingError(err)) {
          // Other errors: surface but keep graph visible
          const detail = err instanceof Error ? err.message : String(err);
          setError(detail);
        }
        setEdges([]);
      } finally {
        if (!cancelled) setEdgesLoaded(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [viewMode, edgesLoaded, loadingList]);

  const selectedIdea = useMemo(
    () => (selectedId ? ideas.find((i) => i.id === selectedId) ?? null : null),
    [ideas, selectedId],
  );

  // Auto-resize textarea like CompilerPage
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = Math.min(Math.max(el.scrollHeight, 56), 240) + 'px';
  }, [input]);

  useEffect(() => {
    return () => {
      recognitionRef.current?.abort();
      recognitionRef.current = null;
    };
  }, []);

  // Load existing ideas on mount
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await apiFetch<ListResponse>('/idea_atlas/ideas');
        if (cancelled) return;
        setIdeas(Array.isArray(data) ? data : []);
        setEdgesLoaded(false);
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

  useEffect(() => {
    if (!selectedId) return;
    if (!ideas.some((idea) => idea.id === selectedId)) {
      setSelectedId(null);
    }
  }, [ideas, selectedId]);

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
        prev.map((it) => (it.id === placeholderId ? data : it)),
      );
      setRecentIdeaId(data.id);
      setEdgesLoaded(false);
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

  const stopSpeechCapture = useCallback(() => {
    const recognition = recognitionRef.current;
    if (!recognition) {
      setListening(false);
      return;
    }
    recognition.stop();
  }, []);

  const startSpeechCapture = useCallback(() => {
    if (listening) return;
    if (backendState === 'unavailable') {
      setSpeechStatus('Speech capture is disabled while the Idea Atlas backend is unavailable.');
      return;
    }

    const RecognitionCtor = getSpeechRecognitionCtor();
    if (!RecognitionCtor) {
      setSpeechStatus('Speech capture is not available in this browser. Chrome and Edge support it best.');
      return;
    }

    try {
      const recognition = new RecognitionCtor();
      speechBaseRef.current = input.trim();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = 'en-US';
      recognition.onstart = () => {
        setListening(true);
        setSpeechStatus('Listening... release the button to stop.');
      };
      recognition.onresult = (event) => {
        let spoken = '';
        for (let i = 0; i < event.results.length; i += 1) {
          spoken += event.results[i]?.[0]?.transcript ?? '';
        }
        const transcript = spoken.trim();
        const base = speechBaseRef.current;
        setInput([base, transcript].filter(Boolean).join(base ? ' ' : ''));
      };
      recognition.onerror = (event) => {
        const errorCode = event.error ?? 'speech_error';
        const friendly =
          errorCode === 'not-allowed'
            ? 'Microphone permission was blocked.'
            : errorCode === 'no-speech'
              ? 'No speech was detected. Hold the button and speak clearly.'
              : event.message || `Speech capture stopped: ${errorCode}.`;
        setSpeechStatus(friendly);
      };
      recognition.onend = () => {
        setListening(false);
        recognitionRef.current = null;
        setSpeechStatus((current) =>
          current === 'Listening... release the button to stop.'
            ? 'Speech captured. Edit the text or press Capture.'
            : current,
        );
      };
      recognitionRef.current = recognition;
      recognition.start();
    } catch (err) {
      setListening(false);
      recognitionRef.current = null;
      setSpeechStatus(err instanceof Error ? err.message : String(err));
    }
  }, [backendState, input, listening]);

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  }

  // ── Sprint 3 handlers: invert + delete ──
  const handleInvertClicked = useCallback((idea: Idea) => {
    setInvertingIdea(idea);
  }, []);

  const handleInvertConfirm = useCallback(
    async ({ invertedCas, axis }: { invertedCas: string; axis: string }) => {
      if (!invertingIdea) return;
      // Persist the inverted result as a NEW idea so the graph keeps the
      // original alongside its inversion. Annotate text with the axis tag.
      const invertedText = `${invertingIdea.text}  [inverted via axis ${axis}]`;
      try {
        const data = await apiFetch<CaptureResponse>('/idea_atlas/ideas', {
          method: 'POST',
          body: JSON.stringify({
            text: invertedText,
            cas_expression: invertedCas,
          }),
        });
        setIdeas((prev) => [data, ...prev]);
        setInvertingIdea(null);
        // Force edges refetch on next graph view so the new node connects.
        setEdgesLoaded(false);
        setRecentIdeaId(data.id);
        setSelectedId(data.id);
      } catch (err) {
        const detail = err instanceof Error ? err.message : String(err);
        setError(detail);
      }
    },
    [invertingIdea],
  );

  const handleDeleteClicked = useCallback(async (idea: Idea) => {
    if (!window.confirm(`Delete this idea?\n\n${idea.text}`)) return;
    if (idea.id.startsWith('pending-')) {
      setIdeas((prev) => prev.filter((it) => it.id !== idea.id));
      setSelectedId((cur) => (cur === idea.id ? null : cur));
      setEdgesLoaded(false);
      return;
    }
    try {
      await apiFetch(`/idea_atlas/ideas/${idea.id}`, { method: 'DELETE' });
      setIdeas((prev) => prev.filter((it) => it.id !== idea.id));
      setSelectedId((cur) => (cur === idea.id ? null : cur));
      setEdgesLoaded(false);
    } catch (err) {
      const detail = err instanceof Error ? err.message : String(err);
      setError(detail);
    }
  }, []);

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
      <div className="border-b border-white/[0.06] px-6 py-4 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-accent-teal font-mono text-lg font-semibold">
            Idea Atlas
          </h1>
          <p className="text-slate-500 text-xs mt-1 font-sans">
            Your personal cognitive map. Capture your ideas; see their CAS structure.
          </p>
        </div>
        {/* View-mode toggle: LIST (default — preserves Sprint-1 behavior) | GRAPH */}
        <div
          role="tablist"
          aria-label="View mode"
          className="inline-flex shrink-0 rounded border border-white/[0.06] bg-black/30 p-0.5 font-mono text-[11px]"
        >
          <button
            type="button"
            role="tab"
            aria-selected={viewMode === 'list'}
            onClick={() => setViewMode('list')}
            className={`px-3 py-1 rounded transition-colors ${
              viewMode === 'list'
                ? 'bg-accent-teal/20 text-accent-teal'
                : 'text-slate-500 hover:text-slate-300'
            }`}
          >
            LIST
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={viewMode === 'graph'}
            onClick={() => setViewMode('graph')}
            className={`px-3 py-1 rounded transition-colors ${
              viewMode === 'graph'
                ? 'bg-accent-teal/20 text-accent-teal'
                : 'text-slate-500 hover:text-slate-300'
            }`}
          >
            GRAPH
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={viewMode === 'trace'}
            onClick={() => setViewMode('trace')}
            className={`px-3 py-1 rounded transition-colors ${
              viewMode === 'trace'
                ? 'bg-accent-teal/20 text-accent-teal'
                : 'text-slate-500 hover:text-slate-300'
            }`}
          >
            TRACE
          </button>
        </div>
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
            <div className="mt-2 flex flex-wrap items-center justify-between gap-3">
              <span className="text-[10px] text-slate-600 font-mono">
                Enter to capture, Shift+Enter for newline
              </span>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  aria-pressed={listening}
                  title={speechSupported ? 'Hold while speaking to add words to the idea box.' : 'Speech capture is not available in this browser.'}
                  onPointerDown={(event) => {
                    event.preventDefault();
                    startSpeechCapture();
                  }}
                  onPointerUp={(event) => {
                    event.preventDefault();
                    stopSpeechCapture();
                  }}
                  onPointerLeave={() => {
                    if (listening) stopSpeechCapture();
                  }}
                  onPointerCancel={stopSpeechCapture}
                  onKeyDown={(event) => {
                    if ((event.key === 'Enter' || event.key === ' ') && !listening) {
                      event.preventDefault();
                      startSpeechCapture();
                    }
                  }}
                  onKeyUp={(event) => {
                    if (event.key === 'Enter' || event.key === ' ') {
                      event.preventDefault();
                      stopSpeechCapture();
                    }
                  }}
                  className={`rounded border px-3 py-1.5 font-mono text-xs transition-colors ${
                    listening
                      ? 'border-red-400/50 bg-red-500/15 text-red-200 shadow-[0_0_18px_rgba(248,113,113,0.18)]'
                      : 'border-cyan-400/25 bg-cyan-500/10 text-cyan-300 hover:bg-cyan-500/20'
                  }`}
                >
                  {listening ? 'Listening...' : 'Hold to Speak'}
                </button>
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
            {speechStatus && (
              <p className={`mt-2 text-[10px] font-mono ${listening ? 'text-red-300' : 'text-slate-500'}`}>
                {speechStatus}
              </p>
            )}
          </div>
        </div>

        {error && (
          <div className="mt-3 rounded border border-red-500/20 bg-red-500/[0.05] p-2 font-mono text-[11px] text-red-400">
            {error}
          </div>
        )}
      </div>

      {/* List area (default) — preserved as Agent F shipped it */}
      {viewMode === 'list' && (
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
                className={`animate-[fadeSlideIn_0.25s_ease-out] rounded-lg border p-4 font-mono text-xs ${rippleClass(idea.id)} ${
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
                <div className="mt-2 flex items-center justify-between gap-2">
                  <p className="text-[9px] uppercase tracking-wider text-slate-600">
                    {formatTimestamp(idea.created_at)}
                  </p>
                  <button
                    type="button"
                    onClick={() => handleDeleteClicked(idea)}
                    disabled={isPending(idea)}
                    className="rounded border border-red-500/20 bg-red-500/[0.04] px-2 py-1 font-mono text-[10px] text-red-400 transition-colors hover:bg-red-500/10 disabled:cursor-not-allowed disabled:opacity-35 disabled:hover:bg-red-500/[0.04]"
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
      )}

      {/* Graph view — Sprint 2 */}
      {viewMode === 'graph' && (
        <div className="flex-1 overflow-hidden px-6 py-4">
          {backendState === 'unavailable' ? (
            <div className="rounded-lg border border-amber-500/20 bg-amber-500/[0.04] p-6 text-center">
              <p className="text-amber-400 font-mono text-sm">
                Backend not yet available
              </p>
              <p className="text-slate-500 text-xs mt-2 font-sans">
                The Idea Atlas API endpoint hasn&apos;t been deployed yet.
              </p>
            </div>
          ) : (
            <div className="flex justify-center">
              <GraphView
                ideas={ideas}
                edges={edges}
                selectedId={selectedId}
                pulseId={recentIdeaId}
                onSelectIdea={setSelectedId}
                width={800}
                height={560}
              />
            </div>
          )}
        </div>
      )}

      {/* Sliding detail panel — overlay above graph */}
      {viewMode === 'graph' && (
        <NodeDetailPanel
          idea={selectedIdea}
          onClose={() => setSelectedId(null)}
          onInvertClicked={handleInvertClicked}
          onDeleteClicked={handleDeleteClicked}
        />
      )}

      {/* Inversion modal — Sprint 3 */}
      <InversionModal
        idea={invertingIdea}
        onClose={() => setInvertingIdea(null)}
        onConfirm={handleInvertConfirm}
      />

      {/* Trace view — Atlas v0 */}
      {viewMode === 'trace' && (
        <div className="flex-1 overflow-y-auto px-6 py-4 flex flex-col gap-4">
          <TraceLoader
            onTraceLoaded={handleTraceLoaded}
            onError={handleTraceError}
          />
          {traceError && (
            <div className="rounded border border-rose-500/30 bg-rose-500/10 px-4 py-2 text-xs font-mono text-rose-300">
              {traceError}
            </div>
          )}
          {loadedTrace && (
            <>
            <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-emerald-500/20 bg-emerald-500/[0.05] px-4 py-3 font-mono text-xs text-emerald-200">
              <span>
                Trace loaded: {loadedTrace.thought_tree.node_count} nodes,{' '}
                {loadedTrace.thought_tree.edge_count} edges. Click a node in the
                tree to inspect it.
              </span>
              <button
                type="button"
                onClick={() => setTracePanelOpen((open) => !open)}
                className="rounded border border-emerald-400/30 bg-black/20 px-3 py-1 text-[10px] uppercase tracking-wide text-emerald-100 transition-colors hover:bg-emerald-500/10"
              >
                {tracePanelOpen ? 'Hide Details' : 'Show Details'}
              </button>
            </div>
            <div
              className={`min-h-[560px] grid grid-cols-1 gap-4 ${
                tracePanelOpen ? 'lg:grid-cols-[minmax(0,1fr)_360px]' : ''
              }`}
            >
              {/* Tree on the left */}
              <div className="min-h-[520px] rounded-lg border border-white/[0.06] bg-black/30 overflow-hidden">
                <ThoughtTreeView
                  tree={loadedTrace.thought_tree as unknown as TreeViewTree}
                  onNodeClick={(n) => {
                    setSelectedTraceNodeId(n.id);
                    setTracePanelOpen(true);
                  }}
                  selectedNodeId={selectedTraceNodeId}
                  className="h-full w-full"
                />
              </div>
              {/* Side panel — trace metadata + selected node detail */}
              {tracePanelOpen && (
              <aside className="min-h-[520px] rounded-lg border border-white/[0.06] bg-black/30 p-4 overflow-y-auto font-mono text-[11px] text-slate-300">
                <div className="mb-3 flex items-start justify-between gap-3">
                  <div className="text-accent-teal text-xs font-bold">
                    TRACE DETAILS
                  </div>
                  <button
                    type="button"
                    onClick={() => setTracePanelOpen(false)}
                    className="rounded border border-white/[0.08] px-2 py-1 text-[10px] uppercase text-slate-400 transition-colors hover:border-emerald-400/30 hover:text-emerald-200"
                  >
                    Collapse
                  </button>
                </div>
                <header className="mb-3">
                  <div className="text-accent-teal text-xs font-bold">
                    TRACE METADATA
                  </div>
                  <div className="text-slate-500 text-[10px] mt-1">
                    {loadedTrace.trace_id}
                  </div>
                  <div className="text-slate-500 text-[10px]">
                    {loadedTrace.created_at}
                  </div>
                </header>
                <dl className="space-y-2">
                  <div>
                    <dt className="text-slate-500 text-[10px] uppercase">
                      Input kind
                    </dt>
                    <dd className="text-slate-200">
                      {loadedTrace.input.input_kind}
                    </dd>
                  </div>
                  {loadedTrace.input.input_kind === 'nl_bridge' && (
                    <>
                      <div>
                        <dt className="text-slate-500 text-[10px] uppercase">
                          User text
                        </dt>
                        <dd className="text-slate-100 italic">
                          &ldquo;{loadedTrace.input.user_text}&rdquo;
                        </dd>
                      </div>
                      <div>
                        <dt className="text-slate-500 text-[10px] uppercase">
                          Matched pattern
                        </dt>
                        <dd className="text-slate-200">
                          {loadedTrace.input.nl_bridge.matched_pattern}
                        </dd>
                      </div>
                      <div>
                        <dt className="text-slate-500 text-[10px] uppercase">
                          Confidence
                        </dt>
                        <dd className="text-slate-200">
                          {loadedTrace.input.nl_bridge.confidence.toFixed(2)}
                        </dd>
                      </div>
                      <div>
                        <dt className="text-slate-500 text-[10px] uppercase">
                          Inferred CAS
                        </dt>
                        <dd className="text-accent-teal">
                          {loadedTrace.input.nl_bridge.inferred_cas_expression}
                        </dd>
                      </div>
                      <div>
                        <dt className="text-slate-500 text-[10px] uppercase">
                          Rationale
                        </dt>
                        <dd className="text-slate-200">
                          {loadedTrace.input.nl_bridge.rationale}
                        </dd>
                      </div>
                    </>
                  )}
                  {loadedTrace.input.input_kind === 'cas_expression' && (
                    <div>
                      <dt className="text-slate-500 text-[10px] uppercase">
                        CAS expression
                      </dt>
                      <dd className="text-accent-teal">
                        {loadedTrace.input.cas_expression}
                      </dd>
                    </div>
                  )}
                  <div>
                    <dt className="text-slate-500 text-[10px] uppercase">
                      Generated English
                    </dt>
                    <dd className="text-slate-100">
                      {loadedTrace.output.english}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-slate-500 text-[10px] uppercase">
                      Coverage
                    </dt>
                    <dd className="text-slate-200">
                      {loadedTrace.confidence.qualitative_coverage}
                    </dd>
                  </div>
                  {loadedTrace.confidence.warning_flags.length > 0 && (
                    <div>
                      <dt className="text-slate-500 text-[10px] uppercase">
                        Warnings
                      </dt>
                      <dd className="space-y-1">
                        {loadedTrace.confidence.warning_flags.map((flag, i) => (
                          <div
                            key={i}
                            className={`text-[10px] px-2 py-1 rounded ${
                              flag.severity === 'error'
                                ? 'bg-rose-500/15 text-rose-300'
                                : flag.severity === 'warning'
                                  ? 'bg-amber-500/15 text-amber-300'
                                  : 'bg-slate-500/15 text-slate-300'
                            }`}
                          >
                            {flag.message}
                          </div>
                        ))}
                      </dd>
                    </div>
                  )}
                </dl>
                {selectedTraceNode && (
                  <section
                    ref={selectedNodeSectionRef}
                    className="mt-4 rounded bg-emerald-500/[0.06] border border-emerald-400/30 p-3"
                  >
                    <div className="text-emerald-300 text-xs font-bold mb-2">
                      SELECTED NODE
                    </div>
                    <dl className="space-y-2">
                      <div>
                        <dt className="text-slate-500 text-[10px] uppercase">
                          Kind
                        </dt>
                        <dd className="text-slate-200">
                          {selectedTraceNode.kind}
                        </dd>
                      </div>
                      <div>
                        <dt className="text-slate-500 text-[10px] uppercase">
                          Role
                        </dt>
                        <dd className="text-slate-200">
                          {selectedTraceNode.role}
                        </dd>
                      </div>
                      <div>
                        <dt className="text-slate-500 text-[10px] uppercase">
                          Label
                        </dt>
                        <dd className="text-slate-100">
                          {selectedTraceNode.label}
                        </dd>
                      </div>
                      {selectedTraceNode.text && (
                        <div>
                          <dt className="text-slate-500 text-[10px] uppercase">
                            Text
                          </dt>
                          <dd className="text-slate-100">
                            {selectedTraceNode.text}
                          </dd>
                        </div>
                      )}
                    </dl>
                  </section>
                )}
              </aside>
              )}
            </div>
            </>
          )}
          {!loadedTrace && !traceError && (
            <div className="rounded-lg border border-white/[0.06] bg-black/20 p-6 text-center font-mono text-xs text-slate-500">
              Load a traceability_v0 JSON to see the Thought Tree.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
