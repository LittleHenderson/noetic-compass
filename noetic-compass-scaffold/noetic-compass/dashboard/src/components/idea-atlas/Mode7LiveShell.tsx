import {
  lazy,
  Suspense,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type FormEvent,
} from 'react';
import {
  authenticatedSggsEventSource,
  mode7LiveUrl,
} from '../../api/sggs';
import {
  useSggsLiveTree,
  type SggsCommit,
  type SggsStreamStatus,
} from '../../lib/sggs_stream';
import type {
  AtlasTraceThoughtTree,
  ThoughtTreeEdge,
  ThoughtTreeNode,
  ThoughtTreeRootNode,
} from '../../lib/trace';
import { SggsErrorBoundary } from './SggsErrorBoundary';

const SggsScene = lazy(() =>
  import('./SggsScene').then((m) => ({
    default: m.SggsScene,
  })),
);

interface Mode7Request {
  prompt: string;
  source: string;
  runId: number;
}

interface Mode7EventView {
  id: string;
  nodeId: string | null;
  kind: string;
  label: string;
  detail: string;
}

const DEFAULT_PROMPT =
  'Trace the first principles behind a stakeholder decision and grow the CAS Native AI thought tree as evidence arrives.';
const DEFAULT_SOURCE = 'CAS Native AI traceability stream';

function shortLabel(value: string, fallback: string, max = 54): string {
  const trimmed = value.trim() || fallback;
  return trimmed.length > max ? `${trimmed.slice(0, max - 3)}...` : trimmed;
}

function rootNode(
  id: string,
  kind: string,
  role: string,
  label: string,
  text: string,
  children: ThoughtTreeRootNode[] = [],
): ThoughtTreeRootNode {
  return {
    id,
    node_key: `${kind}|${role}|${label}`,
    kind,
    role,
    label,
    normalized_label: label.toLowerCase(),
    text,
    children,
  };
}

function flattenTree(root: ThoughtTreeRootNode): {
  nodes: ThoughtTreeNode[];
  edges: ThoughtTreeEdge[];
} {
  const nodes: ThoughtTreeNode[] = [];
  const edges: ThoughtTreeEdge[] = [];

  function visit(node: ThoughtTreeRootNode, parent: ThoughtTreeRootNode | null) {
    const nodeId = node.id ?? node.node_key ?? node.label;
    const nodeKey = node.node_key ?? nodeId;
    if (!nodeId) return;
    nodes.push({
      id: nodeId,
      node_key: nodeKey,
      kind: node.kind,
      role: node.role,
      label: node.label,
      normalized_label: node.normalized_label,
      axis_attrs: node.axis_attrs,
      text: node.text,
    });
    const parentId = parent?.id ?? parent?.node_key;
    const parentKey = parent?.node_key ?? parentId;
    if (parentId && parentKey) {
      edges.push({
        id: `idle-${parentId}-${nodeId}`,
        edge_key: `${parentKey}->${nodeKey}`,
        source: parentId,
        target: nodeId,
        source_key: parentKey,
        target_key: nodeKey,
        kind: 'mode7_source',
      });
    }
    for (const child of node.children ?? []) {
      visit(child, node);
    }
  }

  visit(root, null);
  return { nodes, edges };
}

function buildIdleTree(prompt: string, source: string): AtlasTraceThoughtTree {
  const root = rootNode(
    'n0',
    'user_prompt',
    'live_prompt',
    shortLabel(prompt, 'Mode 7 live prompt'),
    prompt.trim() || DEFAULT_PROMPT,
    [
      rootNode(
        'mode7-source',
        'nl_bridge',
        'cas_native_source',
        shortLabel(source, 'CAS Native AI source'),
        source.trim() || DEFAULT_SOURCE,
      ),
    ],
  );
  const { nodes, edges } = flattenTree(root);
  return {
    root,
    nodes,
    edges,
    node_count: nodes.length,
    edge_count: edges.length,
  };
}

function requestPrompt(prompt: string, source: string): string {
  const cleanPrompt = prompt.trim() || DEFAULT_PROMPT;
  const cleanSource = source.trim();
  if (!cleanSource || cleanSource === DEFAULT_SOURCE) return cleanPrompt;
  return `${cleanPrompt}\n\nSource: ${cleanSource}`;
}

function expressionFromSource(source: string): string | undefined {
  const trimmed = source.trim();
  if (!trimmed || trimmed === DEFAULT_SOURCE) return undefined;
  return /[<>{}_^]|^[A-Z]{2}-/.test(trimmed) ? trimmed : undefined;
}

function statusLabel(status: SggsStreamStatus, enabled: boolean, endedAt: string | null): string {
  if (enabled && status === 'connecting') return 'Connecting';
  if (enabled && status === 'open') return 'Live';
  if (endedAt) return 'Complete';
  if (status === 'error') return 'Stream error';
  if (status === 'closed') return 'Stopped';
  return 'Ready';
}

function formatLiveTime(value: string | null): string {
  if (!value) return 'not started';
  try {
    return new Date(value).toLocaleTimeString(undefined, {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  } catch {
    return value;
  }
}

function commitEvent(commit: SggsCommit, index: number): Mode7EventView {
  if (commit.kind === 'turn_start') {
    return {
      id: `${index}-${commit.kind}`,
      nodeId: 'n0',
      kind: 'turn start',
      label: 'CAS Native turn started',
      detail: commit.user_text,
    };
  }
  if (commit.kind === 'head_commit') {
    return {
      id: `${index}-${commit.node_id}`,
      nodeId: commit.node_id,
      kind: commit.node_kind.replace(/_/g, ' '),
      label: commit.node_label,
      detail: commit.head_name.replace(/_/g, ' '),
    };
  }
  if (commit.kind === 'edge_commit') {
    return {
      id: `${index}-${commit.edge_id}`,
      nodeId: commit.target_node_id,
      kind: 'edge',
      label: `${commit.source_node_id} -> ${commit.target_node_id}`,
      detail: commit.edge_kind.replace(/_/g, ' '),
    };
  }
  if (commit.kind === 'turn_end') {
    return {
      id: `${index}-${commit.final_trace_id}`,
      nodeId: null,
      kind: 'turn end',
      label: 'Trace complete',
      detail: `${commit.total_heads} heads in ${commit.duration_ms} ms`,
    };
  }
  return {
    id: `${index}-${commit.kind}`,
    nodeId: null,
    kind: commit.kind,
    label: commit.kind === 'warning' ? commit.message : commit.code,
    detail: commit.kind === 'warning' ? commit.severity : commit.message,
  };
}

function FullscreenIcon({ active }: { active: boolean }) {
  if (active) {
    return (
      <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M8 3v3a2 2 0 0 1-2 2H3" />
        <path d="M21 8h-3a2 2 0 0 1-2-2V3" />
        <path d="M3 16h3a2 2 0 0 1 2 2v3" />
        <path d="M16 21v-3a2 2 0 0 1 2-2h3" />
      </svg>
    );
  }
  return (
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M3 7V5a2 2 0 0 1 2-2h2" />
      <path d="M17 3h2a2 2 0 0 1 2 2v2" />
      <path d="M21 17v2a2 2 0 0 1-2 2h-2" />
      <path d="M7 21H5a2 2 0 0 1-2-2v-2" />
    </svg>
  );
}

export function Mode7LiveShell() {
  const [promptDraft, setPromptDraft] = useState(DEFAULT_PROMPT);
  const [sourceDraft, setSourceDraft] = useState(DEFAULT_SOURCE);
  const [activeRequest, setActiveRequest] = useState<Mode7Request | null>(null);
  const [streamEnabled, setStreamEnabled] = useState(false);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>('n0');
  const [fullscreen, setFullscreen] = useState(false);
  const sceneShellRef = useRef<HTMLDivElement | null>(null);

  const streamUrl = useMemo(() => {
    const request = activeRequest ?? {
      prompt: promptDraft,
      source: sourceDraft,
      runId: 0,
    };
    const url = mode7LiveUrl({
      prompt: requestPrompt(request.prompt, request.source),
      expression: expressionFromSource(request.source),
      delayMs: 140,
    });
    return `${url}&run=${request.runId}`;
  }, [activeRequest, promptDraft, sourceDraft]);

  const stream = useSggsLiveTree({
    url: streamUrl,
    enabled: streamEnabled,
    eventSourceFactory: authenticatedSggsEventSource,
  });

  const displayPrompt = activeRequest?.prompt ?? promptDraft;
  const displaySource = activeRequest?.source ?? sourceDraft;
  const tree = stream.tree ?? buildIdleTree(displayPrompt, displaySource);
  const label = statusLabel(stream.status, streamEnabled, stream.state.endedAt);
  const isRunning =
    streamEnabled && (stream.status === 'connecting' || stream.status === 'open');

  const events = useMemo(
    () => stream.state.commits.map(commitEvent).slice(-12).reverse(),
    [stream.state.commits],
  );

  const selectedNode = useMemo(
    () => tree.nodes.find((node) => node.id === selectedNodeId) ?? null,
    [selectedNodeId, tree.nodes],
  );

  useEffect(() => {
    if (selectedNodeId && tree.nodes.some((node) => node.id === selectedNodeId)) {
      return;
    }
    setSelectedNodeId(tree.root.id ?? tree.nodes[0]?.id ?? null);
  }, [selectedNodeId, tree]);

  useEffect(() => {
    const onChange = () => {
      setFullscreen(document.fullscreenElement === sceneShellRef.current);
    };
    document.addEventListener('fullscreenchange', onChange);
    return () => document.removeEventListener('fullscreenchange', onChange);
  }, []);

  const toggleFullscreen = useCallback(() => {
    const el = sceneShellRef.current;
    if (!el) return;
    if (document.fullscreenElement === el) {
      void document.exitFullscreen?.();
    } else {
      void el.requestFullscreen?.();
    }
  }, []);

  const handleStart = useCallback(
    (event?: FormEvent) => {
      event?.preventDefault();
      stream.reset();
      const nextRequest = {
        prompt: promptDraft.trim() || DEFAULT_PROMPT,
        source: sourceDraft.trim() || DEFAULT_SOURCE,
        runId: Date.now(),
      };
      setActiveRequest(nextRequest);
      setSelectedNodeId('n0');
      setStreamEnabled(true);
    },
    [promptDraft, sourceDraft, stream],
  );

  const handleStop = useCallback(() => {
    setStreamEnabled(false);
  }, []);

  return (
    <div className="flex-1 overflow-y-auto px-6 py-4">
      <div className="grid min-h-[640px] grid-cols-1 gap-4 xl:grid-cols-[360px_minmax(0,1fr)]">
        <aside className="flex flex-col gap-4">
          <section className="rounded-lg border border-cyan-400/20 bg-cyan-500/[0.04] p-4">
            <div className="mb-3 flex items-center justify-between gap-3">
              <div>
                <div className="font-mono text-[10px] uppercase tracking-wider text-cyan-300">
                  MODE 7 LIVE
                </div>
                <h2 className="mt-1 font-sans text-lg font-semibold text-slate-100">
                  CAS Native AI live tree
                </h2>
              </div>
              <span
                className={`rounded border px-2 py-1 font-mono text-[10px] uppercase tracking-wider ${
                  label === 'Live'
                    ? 'border-emerald-400/40 bg-emerald-500/15 text-emerald-200'
                    : label === 'Connecting'
                      ? 'border-amber-400/40 bg-amber-500/15 text-amber-200'
                      : label === 'Stream error'
                        ? 'border-rose-400/40 bg-rose-500/15 text-rose-200'
                        : 'border-white/10 bg-white/[0.04] text-slate-300'
                }`}
              >
                {label}
              </span>
            </div>
            <p className="text-sm leading-relaxed text-slate-300">
              CAS Native AI is the source of the growing Mode 7 tree. Each
              streamed commit adds structure to the spatial graph in real time.
            </p>
          </section>

          <form
            onSubmit={handleStart}
            className="rounded-lg border border-white/[0.06] bg-black/30 p-4"
          >
            <label className="block font-mono text-[10px] uppercase tracking-wider text-slate-400">
              Prompt
            </label>
            <textarea
              value={promptDraft}
              onChange={(event) => setPromptDraft(event.target.value)}
              rows={6}
              className="mt-2 min-h-32 w-full resize-y rounded border border-white/[0.08] bg-black/40 px-3 py-2 font-sans text-sm leading-relaxed text-slate-100 placeholder:text-slate-600 focus:border-cyan-300/60 focus:outline-none"
              placeholder="Ask CAS Native AI to grow a Mode 7 tree..."
            />

            <label className="mt-4 block font-mono text-[10px] uppercase tracking-wider text-slate-400">
              Source / CAS expression
            </label>
            <input
              value={sourceDraft}
              onChange={(event) => setSourceDraft(event.target.value)}
              className="mt-2 w-full rounded border border-white/[0.08] bg-black/40 px-3 py-2 font-mono text-xs text-slate-100 placeholder:text-slate-600 focus:border-cyan-300/60 focus:outline-none"
              placeholder="Document name, transcript, or CO-2^C_{F2}"
            />

            <div className="mt-4 flex flex-wrap items-center gap-2">
              <button
                type="submit"
                disabled={isRunning}
                className="rounded border border-emerald-400/30 bg-emerald-500/10 px-3 py-2 font-mono text-xs text-emerald-200 transition-colors hover:bg-emerald-500/20 disabled:cursor-not-allowed disabled:opacity-40"
              >
                Start
              </button>
              <button
                type="button"
                onClick={handleStop}
                disabled={!isRunning}
                className="rounded border border-rose-400/30 bg-rose-500/10 px-3 py-2 font-mono text-xs text-rose-200 transition-colors hover:bg-rose-500/20 disabled:cursor-not-allowed disabled:opacity-40"
              >
                Stop
              </button>
            </div>
          </form>

          <section className="rounded-lg border border-white/[0.06] bg-black/30 p-4 font-mono text-[11px] text-slate-300">
            <div className="mb-3 text-[10px] uppercase tracking-wider text-slate-500">
              Live Status
            </div>
            <dl className="space-y-2">
              <div className="flex items-center justify-between gap-3">
                <dt className="text-slate-500">source</dt>
                <dd className="text-right text-cyan-200">{displaySource}</dd>
              </div>
              <div className="flex items-center justify-between gap-3">
                <dt className="text-slate-500">nodes</dt>
                <dd>{tree.node_count}</dd>
              </div>
              <div className="flex items-center justify-between gap-3">
                <dt className="text-slate-500">edges</dt>
                <dd>{tree.edge_count}</dd>
              </div>
              <div className="flex items-center justify-between gap-3">
                <dt className="text-slate-500">started</dt>
                <dd>{formatLiveTime(stream.state.startedAt)}</dd>
              </div>
              <div className="flex items-center justify-between gap-3">
                <dt className="text-slate-500">last event</dt>
                <dd>{formatLiveTime(stream.state.updatedAt)}</dd>
              </div>
            </dl>
            {(stream.state.warnings.length > 0 || stream.state.streamErrors.length > 0) && (
              <div className="mt-3 border-t border-white/[0.06] pt-3 font-sans text-xs leading-relaxed text-amber-200">
                {stream.state.streamErrors.at(-1) ??
                  stream.state.warnings.at(-1)?.message}
              </div>
            )}
          </section>
        </aside>

        <main className="flex min-w-0 flex-col gap-4">
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-violet-500/20 bg-violet-500/[0.05] px-4 py-3">
            <div>
              <div className="font-mono text-[10px] uppercase tracking-wider text-violet-300">
                Spatial Gesture Graph
              </div>
              <p className="mt-1 text-sm text-slate-300">
                {stream.state.finalTraceId
                  ? `final trace ${stream.state.finalTraceId}`
                  : 'Mode 7 live commits grow this tree from CAS Native AI.'}
              </p>
            </div>
            <button
              type="button"
              onClick={toggleFullscreen}
              aria-label={fullscreen ? 'Exit fullscreen' : 'Enter fullscreen'}
              title={fullscreen ? 'Exit fullscreen' : 'Fullscreen the live tree'}
              className="flex h-9 w-9 items-center justify-center rounded-md border border-white/[0.08] bg-black/30 text-slate-200 transition-colors hover:bg-white/10 hover:text-white"
            >
              <FullscreenIcon active={fullscreen} />
            </button>
          </div>

          <div
            ref={sceneShellRef}
            style={{ height: fullscreen ? '100vh' : 560 }}
            className="relative min-h-[420px] overflow-hidden rounded-lg border-2 border-violet-500/30 bg-black/30"
          >
            <div className="pointer-events-none absolute left-3 top-3 z-20 rounded-md border border-cyan-300/20 bg-black/60 px-3 py-2 backdrop-blur-sm">
              <div className="font-mono text-[9px] uppercase tracking-wider text-cyan-300">
                CAS Native AI
              </div>
              <div className="mt-1 font-mono text-[11px] text-slate-200">
                Mode 7 live growing tree
              </div>
            </div>

            <button
              type="button"
              onClick={toggleFullscreen}
              aria-label={fullscreen ? 'Exit fullscreen' : 'Enter fullscreen'}
              title={fullscreen ? 'Exit fullscreen' : 'Fullscreen the live tree'}
              className="absolute right-3 top-3 z-20 flex h-9 w-9 items-center justify-center rounded-md border border-white/[0.08] bg-black/55 text-slate-200 backdrop-blur-sm transition-colors hover:bg-white/10 hover:text-white"
            >
              <FullscreenIcon active={fullscreen} />
            </button>

            <SggsErrorBoundary>
              <Suspense
                fallback={
                  <div className="absolute inset-0 flex items-center justify-center font-mono text-xs text-slate-400">
                    Loading SGGS live scene...
                  </div>
                }
              >
                <SggsScene
                  tree={tree}
                  onNodeClick={(node) => setSelectedNodeId(node.id)}
                  selectedNodeId={selectedNodeId}
                  className="h-full w-full"
                  fillParent
                />
              </Suspense>
            </SggsErrorBoundary>

            <div className="pointer-events-none absolute bottom-3 right-3 z-20 rounded-md bg-black/55 px-3 py-2 font-mono text-[10px] text-slate-300 backdrop-blur-sm">
              {tree.node_count} nodes | {tree.edge_count} edges | {stream.status}
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
            <section className="rounded-lg border border-white/[0.06] bg-black/30 p-4">
              <div className="mb-3 font-mono text-[10px] uppercase tracking-wider text-slate-500">
                Stream Events
              </div>
              <div className="space-y-2">
                {events.length === 0 ? (
                  <div className="rounded border border-white/[0.06] bg-white/[0.02] px-3 py-2 text-sm text-slate-500">
                    No live commits yet.
                  </div>
                ) : (
                  events.map((event) => (
                    <button
                      key={event.id}
                      type="button"
                      onClick={() => event.nodeId && setSelectedNodeId(event.nodeId)}
                      className={`w-full rounded border px-3 py-2 text-left transition-colors ${
                        selectedNodeId === event.nodeId
                          ? 'border-cyan-300/40 bg-cyan-500/10'
                          : 'border-white/[0.06] bg-white/[0.02] hover:bg-white/[0.05]'
                      }`}
                    >
                      <div className="font-mono text-[10px] uppercase tracking-wider text-cyan-300">
                        {event.kind}
                      </div>
                      <div className="mt-1 text-sm text-slate-100">{event.label}</div>
                      <div className="mt-1 text-xs leading-relaxed text-slate-500">
                        {event.detail}
                      </div>
                    </button>
                  ))
                )}
              </div>
            </section>

            <aside className="rounded-lg border border-white/[0.06] bg-black/30 p-4">
              <div className="font-mono text-[10px] uppercase tracking-wider text-slate-500">
                Selected Node
              </div>
              {selectedNode ? (
                <dl className="mt-3 space-y-3 text-sm">
                  <div>
                    <dt className="font-mono text-[10px] uppercase tracking-wider text-slate-500">
                      label
                    </dt>
                    <dd className="mt-1 text-slate-100">{selectedNode.label}</dd>
                  </div>
                  <div>
                    <dt className="font-mono text-[10px] uppercase tracking-wider text-slate-500">
                      kind
                    </dt>
                    <dd className="mt-1 font-mono text-xs text-cyan-200">
                      {selectedNode.kind}
                    </dd>
                  </div>
                  <div>
                    <dt className="font-mono text-[10px] uppercase tracking-wider text-slate-500">
                      source
                    </dt>
                    <dd className="mt-1 text-slate-300">CAS Native AI</dd>
                  </div>
                  <div>
                    <dt className="font-mono text-[10px] uppercase tracking-wider text-slate-500">
                      detail
                    </dt>
                    <dd className="mt-1 text-xs leading-relaxed text-slate-300">
                      {selectedNode.text}
                    </dd>
                  </div>
                </dl>
              ) : (
                <p className="mt-3 text-sm text-slate-500">
                  Select a node from the live tree.
                </p>
              )}
            </aside>
          </div>
        </main>
      </div>
    </div>
  );
}
