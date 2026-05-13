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

import { useEffect, useRef, useState } from 'react';

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
}

// EventSource readyState constants. Hard-coded so the file does not
// need an import from `lib.dom.d.ts` types at runtime.
export const EVENT_SOURCE_CONNECTING = 0 as const;
export const EVENT_SOURCE_OPEN = 1 as const;
export const EVENT_SOURCE_CLOSED = 2 as const;

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
  // The cast is checked structurally above; downstream consumers
  // discriminate on `kind`.
  return { ok: true, commit: parsed as unknown as SggsCommit };
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
    // the right handler based on the SSE `event:` line. (Default
    // 'message' is unused — our producer always sets an explicit
    // event name.)
    const listeners: Array<{
      kind: string;
      fn: (ev: { data: string; lastEventId?: string }) => void;
    }> = [];
    for (const kind of SGGS_EVENT_KINDS) {
      const fn = handleCommit(kind);
      source.addEventListener(kind, fn);
      listeners.push({ kind, fn });
    }

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
