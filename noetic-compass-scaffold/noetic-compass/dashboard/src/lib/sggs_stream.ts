/**
 * SGGS stream client — subscribes to a head-level structural-commit
 * Server-Sent Events stream from the CAS-Native inference server and
 * exposes parsed commits via a React hook.
 *
 * Wire format authority: `cas-native/inference/sggs_stream.py` and the
 * spec doc `docs/working/sggs_stream_protocol_2026_05_13.md`. Every
 * field on each commit kind mirrors a field there. If the Python
 * producer adds a field, this file should mirror it.
 *
 * Reconnect strategy: the browser-native `EventSource` does this
 * automatically. On reconnect, the browser sends the `Last-Event-ID`
 * header with the id of the last successfully-dispatched event. The
 * server is expected to resume the stream from after that id (replay
 * cache responsibility lives server-side; the client just exposes
 * `lastEventId` so a custom transport can read it on reconnect).
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import type {
  AtlasTraceThoughtTree,
  ThoughtTreeEdge,
  ThoughtTreeNode,
  ThoughtTreeRootNode,
} from './trace';

// ── Schema literal ───────────────────────────────────────────────────────

export const SGGS_STREAM_SCHEMA_VERSION = 'sggs_stream_v0' as const;
export type SggsStreamSchemaVersion = typeof SGGS_STREAM_SCHEMA_VERSION;

// ── Event kind literals (mirrors Python EVENT_KINDS) ─────────────────────

export const SGGS_EVENT_TURN_START = 'turn_start' as const;
export const SGGS_EVENT_HEAD_COMMIT = 'head_commit' as const;
export const SGGS_EVENT_EDGE_COMMIT = 'edge_commit' as const;
export const SGGS_EVENT_TURN_END = 'turn_end' as const;
export const SGGS_EVENT_WARNING = 'warning' as const;
export const SGGS_EVENT_ERROR = 'error' as const;

export type SggsEventKind =
  | typeof SGGS_EVENT_TURN_START
  | typeof SGGS_EVENT_HEAD_COMMIT
  | typeof SGGS_EVENT_EDGE_COMMIT
  | typeof SGGS_EVENT_TURN_END
  | typeof SGGS_EVENT_WARNING
  | typeof SGGS_EVENT_ERROR;

export const SGGS_EVENT_KINDS: readonly SggsEventKind[] = [
  SGGS_EVENT_TURN_START,
  SGGS_EVENT_HEAD_COMMIT,
  SGGS_EVENT_EDGE_COMMIT,
  SGGS_EVENT_TURN_END,
  SGGS_EVENT_WARNING,
  SGGS_EVENT_ERROR,
];

// ── Commit-kind discriminated union ──────────────────────────────────────

export interface SggsTurnStartCommit {
  kind: typeof SGGS_EVENT_TURN_START;
  turn_id: string;
  user_text: string;
  created_at: string;
  schema_version: SggsStreamSchemaVersion;
}

export interface SggsHeadCommit {
  kind: typeof SGGS_EVENT_HEAD_COMMIT;
  turn_id: string;
  head_index: number;
  head_name: string;
  node_id: string;
  node_kind: string;
  node_label: string;
  parent_node_id: string | null;
  axis_attrs: Record<string, unknown>;
  schema_version: SggsStreamSchemaVersion;
}

export interface SggsEdgeCommit {
  kind: typeof SGGS_EVENT_EDGE_COMMIT;
  turn_id: string;
  edge_id: string;
  source_node_id: string;
  target_node_id: string;
  edge_kind: string;
  schema_version: SggsStreamSchemaVersion;
}

export interface SggsTurnEndCommit {
  kind: typeof SGGS_EVENT_TURN_END;
  turn_id: string;
  final_trace_id: string;
  total_heads: number;
  duration_ms: number;
  ended_at: string;
  schema_version: SggsStreamSchemaVersion;
}

export interface SggsWarningCommit {
  kind: typeof SGGS_EVENT_WARNING;
  turn_id: string;
  severity: string;
  message: string;
  schema_version: SggsStreamSchemaVersion;
}

export interface SggsErrorCommit {
  kind: typeof SGGS_EVENT_ERROR;
  turn_id: string;
  code: string;
  message: string;
  schema_version: SggsStreamSchemaVersion;
}

export type SggsCommit =
  | SggsTurnStartCommit
  | SggsHeadCommit
  | SggsEdgeCommit
  | SggsTurnEndCommit
  | SggsWarningCommit
  | SggsErrorCommit;

// ── Connection status ────────────────────────────────────────────────────

export type SggsStreamStatus =
  | 'idle'
  | 'connecting'
  | 'open'
  | 'closed'
  | 'error';

// ── Hook public surface ──────────────────────────────────────────────────

export interface UseSggsStreamOptions {
  /** Endpoint URL the EventSource should subscribe to (e.g.
   * `/api/sggs/stream`). */
  url: string;
  /** Toggle connection without remounting the component. When false the
   * hook closes any existing connection and stays in `idle`. */
  enabled: boolean;
  /** Per-commit callback. Fires once per successfully-parsed event. */
  onCommit: (commit: SggsCommit) => void;
  /** Optional error callback. Fires for malformed JSON, unknown event
   * kinds, or transport errors. The stream stays open on parse errors
   * (a single bad event does not poison the stream); transport errors
   * surface here too but EventSource handles reconnect automatically. */
  onError?: (message: string) => void;
  /** Optional EventSource factory — tests inject `MockEventSource`. Defaults
   * to the browser-native `EventSource`. */
  eventSourceFactory?: (url: string) => EventSourceLike;
}

export interface UseSggsStreamReturn {
  status: SggsStreamStatus;
  lastEventId: string | null;
}

// -- Live tree adapter ------------------------------------------------------

export interface SggsLiveTreeState {
  turnId: string | null;
  userText: string | null;
  startedAt: string | null;
  endedAt: string | null;
  finalTraceId: string | null;
  durationMs: number | null;
  rootNodeId: string | null;
  nodes: ThoughtTreeNode[];
  edges: ThoughtTreeEdge[];
  tree: AtlasTraceThoughtTree | null;
  commits: SggsCommit[];
  warnings: SggsWarningCommit[];
  errors: SggsErrorCommit[];
  streamErrors: string[];
  lastCommit: SggsCommit | null;
  updatedAt: string | null;
}

export interface UseSggsLiveTreeOptions
  extends Omit<UseSggsStreamOptions, 'onCommit' | 'onError'> {
  onCommit?: (commit: SggsCommit, state: SggsLiveTreeState) => void;
  onError?: (message: string, state: SggsLiveTreeState) => void;
}

export interface UseSggsLiveTreeReturn extends UseSggsStreamReturn {
  state: SggsLiveTreeState;
  tree: AtlasTraceThoughtTree | null;
  reset: () => void;
}

// ── EventSource-like interface (for the test mock) ──────────────────────

/** Minimal EventSource shape the hook depends on. Lets the test inject
 * a queue-backed mock without polyfilling all of EventSource. */
export interface EventSourceLike {
  readonly readyState: number;
  addEventListener(
    type: string,
    listener: (ev: { data: string; lastEventId?: string }) => void,
  ): void;
  removeEventListener?(
    type: string,
    listener: (ev: { data: string; lastEventId?: string }) => void,
  ): void;
  close(): void;
  /** Optional — only present on real EventSource. */
  onopen?: ((this: EventSourceLike, ev: Event) => unknown) | null;
  /** Optional — only present on real EventSource. */
  onerror?: ((this: EventSourceLike, ev: Event) => unknown) | null;
  /** Optional — used by fetch-backed streams that complete normally. */
  onclose?: ((this: EventSourceLike) => unknown) | null;
}

// EventSource readyState constants. Hard-coded so the file does not
// need an import from `lib.dom.d.ts` types at runtime.
export const EVENT_SOURCE_CONNECTING = 0 as const;
export const EVENT_SOURCE_OPEN = 1 as const;
export const EVENT_SOURCE_CLOSED = 2 as const;

export interface FetchEventSourceOptions {
  headers?: Record<string, string>;
  fetchImpl?: typeof fetch;
}

interface ParsedSseBlock {
  type: string;
  data: string;
  lastEventId?: string;
}

function takeSseBlock(buffer: string): [string | null, string] {
  const lfIndex = buffer.indexOf('\n\n');
  const crlfIndex = buffer.indexOf('\r\n\r\n');
  if (lfIndex === -1 && crlfIndex === -1) return [null, buffer];
  if (crlfIndex !== -1 && (lfIndex === -1 || crlfIndex < lfIndex)) {
    return [buffer.slice(0, crlfIndex), buffer.slice(crlfIndex + 4)];
  }
  return [buffer.slice(0, lfIndex), buffer.slice(lfIndex + 2)];
}

function parseSseBlock(raw: string): ParsedSseBlock | null {
  let type = 'message';
  let lastEventId: string | undefined;
  const dataLines: string[] = [];

  for (const line of raw.split(/\r?\n/)) {
    if (!line || line.startsWith(':')) continue;
    const separator = line.indexOf(':');
    const field = separator === -1 ? line : line.slice(0, separator);
    const rawValue = separator === -1 ? '' : line.slice(separator + 1);
    const value = rawValue.startsWith(' ') ? rawValue.slice(1) : rawValue;

    if (field === 'event') type = value || 'message';
    if (field === 'id') lastEventId = value;
    if (field === 'data') dataLines.push(value);
  }

  if (dataLines.length === 0) return null;
  return { type, data: dataLines.join('\n'), lastEventId };
}

class FetchEventSource implements EventSourceLike {
  readonly url: string;
  readyState: number = EVENT_SOURCE_CONNECTING;
  onopen: ((this: EventSourceLike, ev: Event) => unknown) | null = null;
  onerror: ((this: EventSourceLike, ev: Event) => unknown) | null = null;
  onclose: ((this: EventSourceLike) => unknown) | null = null;

  private readonly abortController = new AbortController();
  private readonly fetchImpl: typeof fetch;
  private readonly headers: Record<string, string>;
  private readonly listeners = new Map<string, Array<(ev: { data: string; lastEventId?: string }) => void>>();
  private closed = false;

  constructor(url: string, options: FetchEventSourceOptions = {}) {
    this.url = url;
    this.fetchImpl = options.fetchImpl ?? fetch;
    this.headers = options.headers ?? {};
    void this.connect();
  }

  addEventListener(
    type: string,
    listener: (ev: { data: string; lastEventId?: string }) => void,
  ): void {
    const listeners = this.listeners.get(type) ?? [];
    listeners.push(listener);
    this.listeners.set(type, listeners);
  }

  removeEventListener(
    type: string,
    listener: (ev: { data: string; lastEventId?: string }) => void,
  ): void {
    const listeners = this.listeners.get(type) ?? [];
    this.listeners.set(
      type,
      listeners.filter((candidate) => candidate !== listener),
    );
  }

  close(): void {
    if (this.closed) return;
    this.closed = true;
    this.readyState = EVENT_SOURCE_CLOSED;
    this.abortController.abort();
  }

  private dispatch(type: string, ev: { data: string; lastEventId?: string }): void {
    for (const listener of this.listeners.get(type) ?? []) {
      listener(ev);
    }
  }

  private async connect(): Promise<void> {
    try {
      const response = await this.fetchImpl(this.url, {
        method: 'GET',
        headers: {
          Accept: 'text/event-stream',
          ...this.headers,
        },
        credentials: 'same-origin',
        signal: this.abortController.signal,
      });

      if (!response.ok || !response.body) {
        throw new Error(`Mode 7 stream failed with HTTP ${response.status}.`);
      }

      this.readyState = EVENT_SOURCE_OPEN;
      this.onopen?.call(this, new Event('open'));

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (!this.closed) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        while (true) {
          const [block, rest] = takeSseBlock(buffer);
          if (block === null) break;
          buffer = rest;
          const parsed = parseSseBlock(block);
          if (parsed) {
            this.dispatch(parsed.type, {
              data: parsed.data,
              lastEventId: parsed.lastEventId,
            });
          }
        }
      }

      if (buffer.trim()) {
        const parsed = parseSseBlock(buffer);
        if (parsed) {
          this.dispatch(parsed.type, {
            data: parsed.data,
            lastEventId: parsed.lastEventId,
          });
        }
      }

      if (!this.closed) {
        this.readyState = EVENT_SOURCE_CLOSED;
        this.onclose?.call(this);
      }
    } catch {
      if (this.closed) return;
      this.readyState = EVENT_SOURCE_CLOSED;
      this.onerror?.call(this, new Event('error'));
    }
  }
}

export function createFetchEventSource(
  url: string,
  options: FetchEventSourceOptions = {},
): EventSourceLike {
  return new FetchEventSource(url, options);
}

// ── Parsing helpers ──────────────────────────────────────────────────────

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function isSggsEventKind(value: unknown): value is SggsEventKind {
  return (
    typeof value === 'string' &&
    (SGGS_EVENT_KINDS as readonly string[]).includes(value)
  );
}

// ── Per-kind field validators ────────────────────────────────────────────
//
// Codex audit 3f495ba blocker 2 (2026-05-13): the previous parser accepted
// any object whose `kind` was in the known set and whose `turn_id` was a
// string. That meant a malformed `head_commit` missing `node_id` /
// `node_label` would still dispatch through `onCommit` and could corrupt
// the live graph. These validators enforce every field declared by the
// discriminated-union interfaces above + the schema_version.

const REQ_STR_FIELDS: Record<SggsEventKind, readonly string[]> = {
  turn_start: ['user_text', 'created_at'],
  head_commit: ['head_name', 'node_id', 'node_kind', 'node_label'],
  edge_commit: ['edge_id', 'source_node_id', 'target_node_id', 'edge_kind'],
  turn_end: ['final_trace_id', 'ended_at'],
  warning: ['severity', 'message'],
  error: ['code', 'message'],
};

const REQ_NUM_FIELDS: Record<SggsEventKind, readonly string[]> = {
  turn_start: [],
  head_commit: ['head_index'],
  edge_commit: [],
  turn_end: ['total_heads', 'duration_ms'],
  warning: [],
  error: [],
};

function validateCommitFields(
  kind: SggsEventKind,
  payload: Record<string, unknown>,
): string | null {
  if (payload.schema_version !== SGGS_STREAM_SCHEMA_VERSION) {
    return (
      `schema_version expected "${SGGS_STREAM_SCHEMA_VERSION}" ` +
      `got "${String(payload.schema_version)}"`
    );
  }
  for (const field of REQ_STR_FIELDS[kind]) {
    if (typeof payload[field] !== 'string') {
      return `${kind} missing string field "${field}"`;
    }
  }
  for (const field of REQ_NUM_FIELDS[kind]) {
    if (typeof payload[field] !== 'number') {
      return `${kind} missing numeric field "${field}"`;
    }
  }
  if (kind === 'head_commit') {
    // parent_node_id may be string OR null per the type union
    const parent = payload.parent_node_id;
    if (parent !== null && typeof parent !== 'string') {
      return 'head_commit.parent_node_id must be string or null';
    }
    if (!isPlainObject(payload.axis_attrs)) {
      return 'head_commit.axis_attrs must be an object';
    }
  }
  return null;
}

/**
 * Parse a `data:` line payload into a typed `SggsCommit`.
 *
 * Returns `{ ok: true, commit }` on success or `{ ok: false, error }`
 * naming the first failure. Used by the hook AND directly importable
 * for offline trace replay (e.g. piping a recorded SSE log through
 * this parser to reconstruct the commit sequence).
 */
export function parseSggsCommit(
  expectedKind: string,
  rawData: string,
): { ok: true; commit: SggsCommit } | { ok: false; error: string } {
  let parsed: unknown;
  try {
    parsed = JSON.parse(rawData);
  } catch (err) {
    const msg = err instanceof Error ? err.message : 'Unknown JSON parse error.';
    return { ok: false, error: `Could not parse SSE data JSON: ${msg}` };
  }
  if (!isPlainObject(parsed)) {
    return { ok: false, error: 'SSE data was not a JSON object.' };
  }
  const kind = parsed.kind;
  if (!isSggsEventKind(kind)) {
    return {
      ok: false,
      error: `Unknown SGGS event kind: ${String(kind)}`,
    };
  }
  // The event name on the SSE channel and the `kind` field inside the
  // JSON payload should agree. A mismatch suggests the producer wired
  // the wrong helper to the wrong channel — surface it.
  if (expectedKind && kind !== expectedKind) {
    return {
      ok: false,
      error: `SSE event name "${expectedKind}" disagrees with payload kind "${kind}"`,
    };
  }
  if (typeof parsed.turn_id !== 'string') {
    return { ok: false, error: 'commit is missing turn_id.' };
  }
  // Per-kind structural validation (Codex audit 3f495ba blocker 2).
  const fieldError = validateCommitFields(kind, parsed);
  if (fieldError !== null) {
    return { ok: false, error: fieldError };
  }
  // The cast is checked structurally above; downstream consumers
  // discriminate on `kind`.
  return { ok: true, commit: parsed as unknown as SggsCommit };
}

// -- Live tree state accumulation ------------------------------------------

function nowIso(): string {
  return new Date().toISOString();
}

function normalizeNodeLabel(label: string, axisAttrs: Record<string, unknown>): string {
  const normalized = axisAttrs.normalized_label;
  if (typeof normalized === 'string' && normalized.trim()) {
    return normalized;
  }
  return label.trim().toLowerCase();
}

function shortLiveLabel(value: string, fallback: string): string {
  const trimmed = value.trim() || fallback;
  return trimmed.length > 64 ? `${trimmed.slice(0, 61)}...` : trimmed;
}

function rootNodeFromTurnStart(commit: SggsTurnStartCommit): ThoughtTreeNode {
  const label = shortLiveLabel(commit.user_text, 'Mode 7 live prompt');
  return {
    id: 'n0',
    node_key: `mode7|${commit.turn_id}|prompt`,
    kind: 'user_prompt',
    role: 'live_prompt',
    label,
    normalized_label: label.toLowerCase(),
    text: commit.user_text,
  };
}

function nodeFromHeadCommit(commit: SggsHeadCommit): ThoughtTreeNode {
  const text = commit.axis_attrs.text;
  return {
    id: commit.node_id,
    node_key: commit.node_id,
    kind: commit.node_kind,
    role: commit.head_name,
    label: commit.node_label,
    normalized_label: normalizeNodeLabel(commit.node_label, commit.axis_attrs),
    axis_attrs: commit.axis_attrs,
    ...(typeof text === 'string' ? { text } : {}),
  };
}

function edgeFromEdgeCommit(commit: SggsEdgeCommit): ThoughtTreeEdge {
  return {
    id: commit.edge_id,
    edge_key: commit.edge_id,
    source: commit.source_node_id,
    target: commit.target_node_id,
    source_key: commit.source_node_id,
    target_key: commit.target_node_id,
    kind: commit.edge_kind,
  };
}

function syntheticParentEdge(source: string, target: string): ThoughtTreeEdge {
  const id = `parent:${source}->${target}`;
  return {
    id,
    edge_key: id,
    source,
    target,
    source_key: source,
    target_key: target,
    kind: 'parent_child',
  };
}

function upsertNode(nodes: ThoughtTreeNode[], node: ThoughtTreeNode): ThoughtTreeNode[] {
  const index = nodes.findIndex((candidate) => candidate.id === node.id);
  if (index === -1) return [...nodes, node];
  const next = nodes.slice();
  next[index] = { ...next[index], ...node };
  return next;
}

function upsertEdge(edges: ThoughtTreeEdge[], edge: ThoughtTreeEdge): ThoughtTreeEdge[] {
  const explicitEdges = edge.id.startsWith('parent:')
    ? edges
    : edges.filter(
        (candidate) =>
          !(
            candidate.id.startsWith('parent:') &&
            candidate.source === edge.source &&
            candidate.target === edge.target
          ),
      );
  const index = explicitEdges.findIndex((candidate) => candidate.id === edge.id);
  if (index === -1) return [...explicitEdges, edge];
  const next = explicitEdges.slice();
  next[index] = { ...next[index], ...edge };
  return next;
}

function toRootNode(
  node: ThoughtTreeNode,
  children: ThoughtTreeRootNode[],
): ThoughtTreeRootNode {
  return {
    id: node.id,
    node_key: node.node_key,
    kind: node.kind,
    role: node.role,
    label: node.label,
    normalized_label: node.normalized_label,
    ...(node.axis_attrs ? { axis_attrs: node.axis_attrs } : {}),
    ...(node.text ? { text: node.text } : {}),
    ...(children.length > 0 ? { children } : {}),
  };
}

function chooseRootNodeId(
  nodes: ThoughtTreeNode[],
  edges: ThoughtTreeEdge[],
  preferredRootId: string | null,
): string | null {
  if (preferredRootId && nodes.some((node) => node.id === preferredRootId)) {
    return preferredRootId;
  }
  const targets = new Set(edges.map((edge) => edge.target));
  return nodes.find((node) => !targets.has(node.id))?.id ?? nodes[0]?.id ?? null;
}

function buildLiveThoughtTree(
  nodes: ThoughtTreeNode[],
  edges: ThoughtTreeEdge[],
  preferredRootId: string | null,
): AtlasTraceThoughtTree | null {
  const rootId = chooseRootNodeId(nodes, edges, preferredRootId);
  if (!rootId) return null;

  const nodesById = new Map(nodes.map((node) => [node.id, node]));
  const childrenBySource = new Map<string, ThoughtTreeEdge[]>();
  for (const edge of edges) {
    if (!nodesById.has(edge.source) || !nodesById.has(edge.target)) continue;
    const list = childrenBySource.get(edge.source) ?? [];
    list.push(edge);
    childrenBySource.set(edge.source, list);
  }

  const visit = (id: string, seen: Set<string>): ThoughtTreeRootNode | null => {
    const node = nodesById.get(id);
    if (!node || seen.has(id)) return null;
    const nextSeen = new Set(seen);
    nextSeen.add(id);
    const childEdges = childrenBySource.get(id) ?? [];
    const children = childEdges
      .map((edge) => visit(edge.target, nextSeen))
      .filter((child): child is ThoughtTreeRootNode => child !== null);
    return toRootNode(node, children);
  };

  const root = visit(rootId, new Set());
  if (!root) return null;

  return {
    root,
    nodes,
    edges,
    node_count: nodes.length,
    edge_count: edges.length,
  };
}

export function createEmptySggsLiveTreeState(): SggsLiveTreeState {
  return {
    turnId: null,
    userText: null,
    startedAt: null,
    endedAt: null,
    finalTraceId: null,
    durationMs: null,
    rootNodeId: null,
    nodes: [],
    edges: [],
    tree: null,
    commits: [],
    warnings: [],
    errors: [],
    streamErrors: [],
    lastCommit: null,
    updatedAt: null,
  };
}

function withTree(
  state: SggsLiveTreeState,
  nodes: ThoughtTreeNode[],
  edges: ThoughtTreeEdge[],
  rootNodeId = state.rootNodeId,
): Pick<SggsLiveTreeState, 'nodes' | 'edges' | 'rootNodeId' | 'tree'> {
  return {
    nodes,
    edges,
    rootNodeId,
    tree: buildLiveThoughtTree(nodes, edges, rootNodeId),
  };
}

export function applySggsCommitToLiveTree(
  state: SggsLiveTreeState,
  commit: SggsCommit,
): SggsLiveTreeState {
  const base = {
    ...state,
    commits: [...state.commits, commit],
    lastCommit: commit,
    updatedAt: nowIso(),
  };

  switch (commit.kind) {
    case SGGS_EVENT_TURN_START:
      {
        const rootNode = rootNodeFromTurnStart(commit);
        const empty = createEmptySggsLiveTreeState();
        return {
          ...empty,
          turnId: commit.turn_id,
          userText: commit.user_text,
          startedAt: commit.created_at,
          commits: [commit],
          lastCommit: commit,
          updatedAt: base.updatedAt,
          ...withTree(empty, [rootNode], [], rootNode.id),
        };
      }

    case SGGS_EVENT_HEAD_COMMIT: {
      const node = nodeFromHeadCommit(commit);
      const nodes = upsertNode(base.nodes, node);
      const rootNodeId =
        commit.parent_node_id === null && base.rootNodeId === null
          ? commit.node_id
          : base.rootNodeId;
      const parentNodeId =
        commit.parent_node_id ??
        (base.rootNodeId && commit.node_id !== base.rootNodeId ? base.rootNodeId : null);
      const edges =
        parentNodeId === null
          ? base.edges
          : upsertEdge(
              base.edges,
              syntheticParentEdge(parentNodeId, commit.node_id),
            );
      return {
        ...base,
        turnId: base.turnId ?? commit.turn_id,
        ...withTree(base, nodes, edges, rootNodeId),
      };
    }

    case SGGS_EVENT_EDGE_COMMIT: {
      const edges = upsertEdge(base.edges, edgeFromEdgeCommit(commit));
      return {
        ...base,
        turnId: base.turnId ?? commit.turn_id,
        ...withTree(base, base.nodes, edges),
      };
    }

    case SGGS_EVENT_TURN_END:
      return {
        ...base,
        turnId: base.turnId ?? commit.turn_id,
        endedAt: commit.ended_at,
        finalTraceId: commit.final_trace_id,
        durationMs: commit.duration_ms,
      };

    case SGGS_EVENT_WARNING:
      return {
        ...base,
        turnId: base.turnId ?? commit.turn_id,
        warnings: [...base.warnings, commit],
      };

    case SGGS_EVENT_ERROR:
      return {
        ...base,
        turnId: base.turnId ?? commit.turn_id,
        errors: [...base.errors, commit],
      };
  }
}

// ── Hook ─────────────────────────────────────────────────────────────────

/**
 * Subscribe to an SGGS SSE stream and dispatch parsed commits.
 *
 * Reconnect: on transient disconnect, the browser-native EventSource
 * sends `Last-Event-ID: <id>` automatically on the reconnect attempt.
 * The hook tracks the last successfully-dispatched id in component
 * state so external consumers (status panels, dev tools) can render
 * "currently at event 0a1b2c…" without subscribing twice.
 *
 * Parse-error policy: a single malformed event invokes `onError` but
 * does NOT close the stream. Transport-level errors surface via
 * `onError` too; the EventSource handles reconnect itself.
 */
export function useSggsStream(opts: UseSggsStreamOptions): UseSggsStreamReturn {
  const { url, enabled, onCommit, onError, eventSourceFactory } = opts;
  const [status, setStatus] = useState<SggsStreamStatus>('idle');
  const [lastEventId, setLastEventId] = useState<string | null>(null);

  // Stable refs for callbacks so the connection effect does not retear
  // on every parent re-render. Matches the pattern used in TraceLoader.
  const onCommitRef = useRef(onCommit);
  const onErrorRef = useRef(onError);
  useEffect(() => {
    onCommitRef.current = onCommit;
  }, [onCommit]);
  useEffect(() => {
    onErrorRef.current = onError;
  }, [onError]);

  useEffect(() => {
    if (!enabled) {
      setStatus('idle');
      return;
    }

    const factory =
      eventSourceFactory ??
      ((u: string): EventSourceLike => {
        // Defensive: in non-browser test environments without
        // EventSource, fall through to an error rather than crashing
        // at module-import time.
        if (typeof EventSource === 'undefined') {
          throw new Error(
            'EventSource is not available in this environment — pass eventSourceFactory.',
          );
        }
        return new EventSource(u) as unknown as EventSourceLike;
      });

    let source: EventSourceLike | null = null;
    try {
      setStatus('connecting');
      source = factory(url);
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setStatus('error');
      onErrorRef.current?.(`Could not open SGGS stream: ${msg}`);
      return;
    }

    const handleCommit = (kind: string) =>
      (ev: { data: string; lastEventId?: string }): void => {
        const result = parseSggsCommit(kind, ev.data);
        if (!result.ok) {
          onErrorRef.current?.(result.error);
          return;
        }
        if (ev.lastEventId) {
          setLastEventId(ev.lastEventId);
        }
        onCommitRef.current(result.commit);
      };

    // Wire one listener per known kind so the browser dispatches to
    // the right handler based on the SSE `event:` line. Also accept
    // default 'message' events and trust the embedded `kind` field.
    const listeners: Array<{
      kind: string;
      fn: (ev: { data: string; lastEventId?: string }) => void;
    }> = [];
    for (const kind of SGGS_EVENT_KINDS) {
      const fn = handleCommit(kind);
      source.addEventListener(kind, fn);
      listeners.push({ kind, fn });
    }
    const defaultMessageHandler = handleCommit('');
    source.addEventListener('message', defaultMessageHandler);
    listeners.push({ kind: 'message', fn: defaultMessageHandler });

    // Status wiring — `onopen` / `onerror` may be undefined on a mock
    // source; guard each.
    const realSource = source as EventSourceLike & {
      onopen?: ((this: EventSourceLike, ev: Event) => unknown) | null;
      onerror?: ((this: EventSourceLike, ev: Event) => unknown) | null;
    };
    if ('onopen' in realSource) {
      realSource.onopen = () => setStatus('open');
    }
    if ('onerror' in realSource) {
      realSource.onerror = () => {
        // EventSource auto-reconnects unless explicitly closed; we
        // report 'error' but expect the next 'open' to flip status
        // back. If the producer hard-closes (readyState=CLOSED) the
        // status sticks as 'closed' via the cleanup below.
        setStatus(
          realSource.readyState === EVENT_SOURCE_CLOSED ? 'closed' : 'error',
        );
        onErrorRef.current?.('SGGS stream transport error.');
      };
    }
    if ('onclose' in realSource) {
      realSource.onclose = () => setStatus('closed');
    }

    return () => {
      // Detach listeners (in environments where removeEventListener is
      // implemented; on real EventSource the close() call disposes them
      // anyway).
      if (source) {
        for (const { kind, fn } of listeners) {
          source.removeEventListener?.(kind, fn);
        }
        source.close();
        setStatus('closed');
      }
    };
    // eventSourceFactory is intentionally captured at mount-time so a
    // test does not have to memoize its mock factory; same pattern as
    // TraceLoader.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [url, enabled]);

  return { status, lastEventId };
}

/**
 * Subscribe to an SGGS stream and accumulate a UI-ready Thought Tree.
 *
 * This adapter is intentionally small: IdeaAtlasPage and CompilerPage can
 * render `tree` directly with the existing ThoughtTreeView/SggsScene once
 * they decide where to mount live Mode 7 output.
 */
export function useSggsLiveTree(
  opts: UseSggsLiveTreeOptions,
): UseSggsLiveTreeReturn {
  const { onCommit, onError, ...streamOpts } = opts;
  const [state, setState] = useState<SggsLiveTreeState>(() =>
    createEmptySggsLiveTreeState(),
  );

  const onCommitRef = useRef(onCommit);
  const onErrorRef = useRef(onError);
  useEffect(() => {
    onCommitRef.current = onCommit;
  }, [onCommit]);
  useEffect(() => {
    onErrorRef.current = onError;
  }, [onError]);

  const handleCommit = useCallback((commit: SggsCommit) => {
    setState((prev) => {
      const next = applySggsCommitToLiveTree(prev, commit);
      onCommitRef.current?.(commit, next);
      return next;
    });
  }, []);

  const handleError = useCallback((message: string) => {
    setState((prev) => {
      const next = {
        ...prev,
        streamErrors: [...prev.streamErrors, message],
        updatedAt: nowIso(),
      };
      onErrorRef.current?.(message, next);
      return next;
    });
  }, []);

  const stream = useSggsStream({
    ...streamOpts,
    onCommit: handleCommit,
    onError: handleError,
  });

  const reset = useCallback(() => {
    setState(createEmptySggsLiveTreeState());
  }, []);

  return {
    ...stream,
    state,
    tree: state.tree,
    reset,
  };
}
