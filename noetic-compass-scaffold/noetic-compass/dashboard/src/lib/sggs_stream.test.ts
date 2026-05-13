/**
 * Tests for `lib/sggs_stream.ts` — the SGGS SSE client.
 *
 * Pins:
 *   - the hook subscribes to a stream and dispatches commits in order;
 *   - `Last-Event-ID` resume semantics: lastEventId reflects the most
 *     recently dispatched commit;
 *   - malformed JSON in a data line invokes onError but does NOT crash;
 *   - closing the stream sets status to 'closed';
 *   - parseSggsCommit narrows the discriminated union correctly.
 *
 * Strategy: a `MockEventSource` implements the minimum surface the hook
 * depends on (addEventListener / removeEventListener / close / readyState
 * constants / onopen / onerror) backed by a queue. Tests push events into
 * the queue and assert callback observations.
 */

import { act, renderHook } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  EVENT_SOURCE_CLOSED,
  EVENT_SOURCE_CONNECTING,
  EVENT_SOURCE_OPEN,
  SGGS_EVENT_EDGE_COMMIT,
  SGGS_EVENT_ERROR,
  SGGS_EVENT_HEAD_COMMIT,
  SGGS_EVENT_TURN_END,
  SGGS_EVENT_TURN_START,
  SGGS_EVENT_WARNING,
  SGGS_STREAM_SCHEMA_VERSION,
  type EventSourceLike,
  type SggsCommit,
  parseSggsCommit,
  useSggsStream,
} from './sggs_stream';

// ── MockEventSource ────────────────────────────────────────────────────

interface MockEvent {
  data: string;
  lastEventId?: string;
}

class MockEventSource implements EventSourceLike {
  static instances: MockEventSource[] = [];
  readonly url: string;
  readyState: number = EVENT_SOURCE_CONNECTING;
  onopen: ((this: EventSourceLike, ev: Event) => unknown) | null = null;
  onerror: ((this: EventSourceLike, ev: Event) => unknown) | null = null;
  private listeners: Map<string, Array<(ev: MockEvent) => void>> = new Map();

  constructor(url: string) {
    this.url = url;
    MockEventSource.instances.push(this);
  }

  addEventListener(type: string, listener: (ev: MockEvent) => void): void {
    const arr = this.listeners.get(type) ?? [];
    arr.push(listener);
    this.listeners.set(type, arr);
  }

  removeEventListener(type: string, listener: (ev: MockEvent) => void): void {
    const arr = this.listeners.get(type);
    if (!arr) return;
    this.listeners.set(
      type,
      arr.filter((fn) => fn !== listener),
    );
  }

  close(): void {
    this.readyState = EVENT_SOURCE_CLOSED;
  }

  // Test helpers — not part of the EventSource interface.
  simulateOpen(): void {
    this.readyState = EVENT_SOURCE_OPEN;
    this.onopen?.call(this, new Event('open'));
  }

  simulateError(closed = false): void {
    if (closed) {
      this.readyState = EVENT_SOURCE_CLOSED;
    }
    this.onerror?.call(this, new Event('error'));
  }

  simulateEvent(type: string, ev: MockEvent): void {
    const arr = this.listeners.get(type) ?? [];
    for (const fn of arr) {
      fn(ev);
    }
  }
}

beforeEach(() => {
  MockEventSource.instances = [];
});

// ── Sample SSE payload helpers (mirrors Python sggs_stream emitters) ──

function turnStartPayload(turn_id = 't-001', user_text = 'hi'): string {
  return JSON.stringify({
    kind: 'turn_start',
    schema_version: SGGS_STREAM_SCHEMA_VERSION,
    turn_id,
    user_text,
    created_at: '2026-05-13T20:00:00Z',
  });
}

function headCommitPayload(
  overrides: Partial<{
    head_index: number;
    head_name: string;
    node_id: string;
    node_kind: string;
    node_label: string;
    parent_node_id: string | null;
    axis_attrs: Record<string, unknown>;
  }> = {},
): string {
  return JSON.stringify({
    kind: 'head_commit',
    schema_version: SGGS_STREAM_SCHEMA_VERSION,
    turn_id: 't-001',
    head_index: 0,
    head_name: 'noetic',
    node_id: 'n1',
    node_kind: 'identifier_attempt',
    node_label: '^3^P|A',
    parent_node_id: 'n0',
    axis_attrs: {},
    ...overrides,
  });
}

function turnEndPayload(): string {
  return JSON.stringify({
    kind: 'turn_end',
    schema_version: SGGS_STREAM_SCHEMA_VERSION,
    turn_id: 't-001',
    final_trace_id: 'trace-uuid',
    total_heads: 1,
    duration_ms: 150,
    ended_at: '2026-05-13T20:00:00Z',
  });
}

// ── parseSggsCommit ────────────────────────────────────────────────────

describe('parseSggsCommit', () => {
  it('parses a well-formed turn_start payload', () => {
    const result = parseSggsCommit('turn_start', turnStartPayload());
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.commit.kind).toBe('turn_start');
      expect(result.commit.turn_id).toBe('t-001');
    }
  });

  it('parses a well-formed head_commit payload', () => {
    const result = parseSggsCommit('head_commit', headCommitPayload());
    expect(result.ok).toBe(true);
    if (result.ok && result.commit.kind === 'head_commit') {
      expect(result.commit.node_id).toBe('n1');
      expect(result.commit.head_index).toBe(0);
    }
  });

  it('rejects malformed JSON', () => {
    const result = parseSggsCommit('head_commit', '{not-json');
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.error).toMatch(/Could not parse SSE data JSON/);
    }
  });

  it('rejects a non-object payload', () => {
    const result = parseSggsCommit('head_commit', '"a string"');
    expect(result.ok).toBe(false);
  });

  it('rejects an unknown event kind', () => {
    const payload = JSON.stringify({ kind: 'fictitious', turn_id: 't' });
    const result = parseSggsCommit('fictitious', payload);
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.error).toMatch(/Unknown SGGS event kind/);
    }
  });

  it('rejects a payload whose embedded kind disagrees with the SSE channel', () => {
    // Channel says head_commit, payload says turn_end. Mismatch is suspicious.
    const result = parseSggsCommit('head_commit', turnEndPayload());
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.error).toMatch(/disagrees/);
    }
  });

  // ── Per-kind validator (Codex audit 3f495ba blocker 2) ──
  // These pin that malformed commits are rejected BEFORE dispatch so
  // a missing/typo'd required field can't corrupt the live graph.

  it('rejects a head_commit missing node_id', () => {
    const payload = JSON.stringify({
      kind: 'head_commit',
      schema_version: SGGS_STREAM_SCHEMA_VERSION,
      turn_id: 't-001',
      head_index: 0,
      head_name: 'noetic',
      // node_id MISSING
      node_kind: 'identifier_attempt',
      node_label: '^3^P|A',
      parent_node_id: 'n0',
      axis_attrs: {},
    });
    const result = parseSggsCommit('head_commit', payload);
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error).toContain('node_id');
  });

  it('rejects a head_commit missing node_label', () => {
    const payload = JSON.stringify({
      kind: 'head_commit',
      schema_version: SGGS_STREAM_SCHEMA_VERSION,
      turn_id: 't-001',
      head_index: 0,
      head_name: 'noetic',
      node_id: 'n1',
      node_kind: 'identifier_attempt',
      // node_label MISSING
      parent_node_id: null,
      axis_attrs: {},
    });
    const result = parseSggsCommit('head_commit', payload);
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error).toContain('node_label');
  });

  it('rejects a head_commit with non-numeric head_index', () => {
    const payload = JSON.stringify({
      kind: 'head_commit',
      schema_version: SGGS_STREAM_SCHEMA_VERSION,
      turn_id: 't-001',
      head_index: 'three',
      head_name: 'noetic',
      node_id: 'n1',
      node_kind: 'identifier_attempt',
      node_label: '^3^P|A',
      parent_node_id: null,
      axis_attrs: {},
    });
    const result = parseSggsCommit('head_commit', payload);
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error).toContain('head_index');
  });

  it('rejects a head_commit with parent_node_id that is not string|null', () => {
    const payload = JSON.stringify({
      kind: 'head_commit',
      schema_version: SGGS_STREAM_SCHEMA_VERSION,
      turn_id: 't-001',
      head_index: 0,
      head_name: 'noetic',
      node_id: 'n1',
      node_kind: 'identifier_attempt',
      node_label: '^3^P|A',
      parent_node_id: 42,
      axis_attrs: {},
    });
    const result = parseSggsCommit('head_commit', payload);
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error).toContain('parent_node_id');
  });

  it('rejects a head_commit whose axis_attrs is not an object', () => {
    const payload = JSON.stringify({
      kind: 'head_commit',
      schema_version: SGGS_STREAM_SCHEMA_VERSION,
      turn_id: 't-001',
      head_index: 0,
      head_name: 'noetic',
      node_id: 'n1',
      node_kind: 'identifier_attempt',
      node_label: '^3^P|A',
      parent_node_id: null,
      axis_attrs: 'not-an-object',
    });
    const result = parseSggsCommit('head_commit', payload);
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error).toContain('axis_attrs');
  });

  it('rejects an edge_commit missing source_node_id', () => {
    const payload = JSON.stringify({
      kind: 'edge_commit',
      schema_version: SGGS_STREAM_SCHEMA_VERSION,
      turn_id: 't-001',
      edge_id: 'e0',
      target_node_id: 'n1',
      edge_kind: 'parent_child',
    });
    const result = parseSggsCommit('edge_commit', payload);
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error).toContain('source_node_id');
  });

  it('rejects a turn_end missing duration_ms', () => {
    const payload = JSON.stringify({
      kind: 'turn_end',
      schema_version: SGGS_STREAM_SCHEMA_VERSION,
      turn_id: 't-001',
      final_trace_id: 'trace-uuid',
      total_heads: 1,
      // duration_ms MISSING
      ended_at: '2026-05-13T20:00:00Z',
    });
    const result = parseSggsCommit('turn_end', payload);
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error).toContain('duration_ms');
  });

  it('rejects a payload with the wrong schema_version', () => {
    const payload = JSON.stringify({
      kind: 'turn_start',
      schema_version: 'sggs_stream_v1', // FUTURE / WRONG
      turn_id: 't-001',
      user_text: 'hi',
      created_at: '2026-05-13T20:00:00Z',
    });
    const result = parseSggsCommit('turn_start', payload);
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error).toContain('schema_version');
  });

  it('rejects a warning commit missing severity', () => {
    const payload = JSON.stringify({
      kind: 'warning',
      schema_version: SGGS_STREAM_SCHEMA_VERSION,
      turn_id: 't-001',
      // severity MISSING
      message: 'coefficients are unfit',
    });
    const result = parseSggsCommit('warning', payload);
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error).toContain('severity');
  });

  it('rejects an error commit missing code', () => {
    const payload = JSON.stringify({
      kind: 'error',
      schema_version: SGGS_STREAM_SCHEMA_VERSION,
      turn_id: 't-001',
      // code MISSING
      message: 'something broke',
    });
    const result = parseSggsCommit('error', payload);
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error).toContain('code');
  });

  it('rejects a payload missing turn_id', () => {
    const payload = JSON.stringify({ kind: 'turn_start' });
    const result = parseSggsCommit('turn_start', payload);
    expect(result.ok).toBe(false);
  });
});

// ── useSggsStream — end-to-end ────────────────────────────────────────

describe('useSggsStream', () => {
  it('subscribes and receives commits in order', () => {
    const commits: SggsCommit[] = [];
    const onCommit = vi.fn((c: SggsCommit) => {
      commits.push(c);
    });
    const factory = (url: string): EventSourceLike => new MockEventSource(url);
    renderHook(() =>
      useSggsStream({
        url: '/api/sggs/stream',
        enabled: true,
        onCommit,
        eventSourceFactory: factory,
      }),
    );

    const source = MockEventSource.instances[0];
    expect(source).toBeDefined();
    act(() => {
      source.simulateOpen();
      source.simulateEvent(SGGS_EVENT_TURN_START, {
        data: turnStartPayload(),
        lastEventId: 'evt-0',
      });
      source.simulateEvent(SGGS_EVENT_HEAD_COMMIT, {
        data: headCommitPayload({ head_index: 0, node_id: 'n1' }),
        lastEventId: 'evt-1',
      });
      source.simulateEvent(SGGS_EVENT_HEAD_COMMIT, {
        data: headCommitPayload({ head_index: 1, node_id: 'n2' }),
        lastEventId: 'evt-2',
      });
      source.simulateEvent(SGGS_EVENT_TURN_END, {
        data: turnEndPayload(),
        lastEventId: 'evt-3',
      });
    });

    expect(onCommit).toHaveBeenCalledTimes(4);
    expect(commits.map((c) => c.kind)).toEqual([
      'turn_start',
      'head_commit',
      'head_commit',
      'turn_end',
    ]);
  });

  it('tracks lastEventId for Last-Event-ID resume', () => {
    const { result } = renderHook(() =>
      useSggsStream({
        url: '/api/sggs/stream',
        enabled: true,
        onCommit: () => undefined,
        eventSourceFactory: (u) => new MockEventSource(u),
      }),
    );

    const source = MockEventSource.instances[0];
    act(() => {
      source.simulateOpen();
      source.simulateEvent(SGGS_EVENT_TURN_START, {
        data: turnStartPayload(),
        lastEventId: 'evt-first',
      });
    });
    expect(result.current.lastEventId).toBe('evt-first');

    act(() => {
      source.simulateEvent(SGGS_EVENT_HEAD_COMMIT, {
        data: headCommitPayload(),
        lastEventId: 'evt-second',
      });
    });
    expect(result.current.lastEventId).toBe('evt-second');
  });

  it('invokes onError on malformed JSON without crashing', () => {
    const onCommit = vi.fn();
    const onError = vi.fn();
    renderHook(() =>
      useSggsStream({
        url: '/api/sggs/stream',
        enabled: true,
        onCommit,
        onError,
        eventSourceFactory: (u) => new MockEventSource(u),
      }),
    );

    const source = MockEventSource.instances[0];
    act(() => {
      source.simulateOpen();
      // First event is bad JSON
      source.simulateEvent(SGGS_EVENT_HEAD_COMMIT, { data: '{bad' });
      // Stream MUST still be alive: emit a valid event after.
      source.simulateEvent(SGGS_EVENT_TURN_END, {
        data: turnEndPayload(),
        lastEventId: 'evt-recovered',
      });
    });

    expect(onError).toHaveBeenCalled();
    // onCommit was NOT called for the bad event but WAS called for the
    // valid one that followed.
    expect(onCommit).toHaveBeenCalledTimes(1);
    expect(onCommit.mock.calls[0]?.[0].kind).toBe('turn_end');
  });

  it('closes the source and sets status to closed on unmount', () => {
    const { unmount, result } = renderHook(() =>
      useSggsStream({
        url: '/api/sggs/stream',
        enabled: true,
        onCommit: () => undefined,
        eventSourceFactory: (u) => new MockEventSource(u),
      }),
    );

    const source = MockEventSource.instances[0];
    act(() => {
      source.simulateOpen();
    });
    expect(result.current.status).toBe('open');

    unmount();
    expect(source.readyState).toBe(EVENT_SOURCE_CLOSED);
  });

  it('stays idle when enabled=false', () => {
    const { result } = renderHook(() =>
      useSggsStream({
        url: '/api/sggs/stream',
        enabled: false,
        onCommit: () => undefined,
        eventSourceFactory: (u) => new MockEventSource(u),
      }),
    );
    expect(result.current.status).toBe('idle');
    expect(MockEventSource.instances.length).toBe(0);
  });

  it('handles edge_commit, warning, and error events', () => {
    const commits: SggsCommit[] = [];
    renderHook(() =>
      useSggsStream({
        url: '/api/sggs/stream',
        enabled: true,
        onCommit: (c) => {
          commits.push(c);
        },
        eventSourceFactory: (u) => new MockEventSource(u),
      }),
    );

    const source = MockEventSource.instances[0];
    act(() => {
      source.simulateOpen();
      source.simulateEvent(SGGS_EVENT_EDGE_COMMIT, {
        data: JSON.stringify({
          kind: 'edge_commit',
          schema_version: SGGS_STREAM_SCHEMA_VERSION,
          turn_id: 't-001',
          edge_id: 'e0',
          source_node_id: 'n0',
          target_node_id: 'n1',
          edge_kind: 'parent_child',
        }),
        lastEventId: 'evt-e0',
      });
      source.simulateEvent(SGGS_EVENT_WARNING, {
        data: JSON.stringify({
          kind: 'warning',
          schema_version: SGGS_STREAM_SCHEMA_VERSION,
          turn_id: 't-001',
          severity: 'info',
          message: 'fyi',
        }),
        lastEventId: 'evt-w0',
      });
      source.simulateEvent(SGGS_EVENT_ERROR, {
        data: JSON.stringify({
          kind: 'error',
          schema_version: SGGS_STREAM_SCHEMA_VERSION,
          turn_id: 't-001',
          code: 'boom',
          message: 'kaboom',
        }),
        lastEventId: 'evt-x0',
      });
    });

    expect(commits.map((c) => c.kind)).toEqual([
      'edge_commit',
      'warning',
      'error',
    ]);
  });

  it('surfaces transport errors via onError', () => {
    const onError = vi.fn();
    renderHook(() =>
      useSggsStream({
        url: '/api/sggs/stream',
        enabled: true,
        onCommit: () => undefined,
        onError,
        eventSourceFactory: (u) => new MockEventSource(u),
      }),
    );

    const source = MockEventSource.instances[0];
    act(() => {
      source.simulateError(/* closed = */ false);
    });
    expect(onError).toHaveBeenCalled();
  });
});
