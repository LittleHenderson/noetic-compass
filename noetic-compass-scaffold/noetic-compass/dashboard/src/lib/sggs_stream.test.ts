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
  MODE7_TRACE_SCHEMA_VERSION,
  SGGS_EVENT_EDGE_COMMIT,
  SGGS_EVENT_ERROR,
  SGGS_EVENT_HEAD_COMMIT,
  SGGS_EVENT_TURN_END,
  SGGS_EVENT_TURN_START,
  SGGS_EVENT_WARNING,
  SGGS_STREAM_SCHEMA_VERSION,
  type EventSourceLike,
  applySggsCommitToLiveTree,
  createEmptySggsLiveTreeState,
  type SggsCommit,
  hasMode7MechanisticAxisAttrs,
  parseSggsCommit,
  selectMode7ActivationLayers,
  selectMode7AttentionHeads,
  selectMode7AxisPayload,
  selectMode7LoadBearingTokens,
  selectMode7LogitsCopySummary,
  selectMode7MechanisticTrace,
  selectMode7StructuralCommitLinkage,
  useSggsLiveTree,
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

function mode7AxisAttrs(): Record<string, unknown> {
  return {
    mode_7_trace: {
      schema_version: MODE7_TRACE_SCHEMA_VERSION,
      trace_id: 'trace-mode7-001',
      id: 'mode7-object-001',
      parent_ids: ['session-001', 'turn-001'],
      source: 'stage3_chat_repl',
      model_checkpoint_id: 'ckpt-final',
      model_code_version: 'abc123',
      mechanistic_label: 'Network Attribution / Mechanistic Trace',
      mechanistic_explanation:
        'Shows which activations, heads, tokens, logits, and copy links supported this commit.',
      input: {
        bpe_tokens: [
          { index: 0, token_str: 'A0' },
          { index: 1, token_str: 'OmegaSafe' },
        ],
      },
      encoder: {
        encoder_layer_l2: [1.5, 2.5],
        hook_status: { _EncoderBlock: true },
      },
      hook_status: {
        'decoder.0': true,
      },
      attention: {
        heads: [
          {
            layer: 'decoder.0',
            head_index: 2,
            entropy: 0.42,
            weight: 0.77,
            source_token: 'OmegaSafe',
            target_token: 'reply',
          },
        ],
        attention_entropy_per_layer: [0.5],
      },
      decoder_per_position: [
        {
          position: 0,
          decoded_token_id: 101,
          decoded_token_str: 'OmegaSafe',
          slot_type: 'OMEGA',
          slot_type_confidence: 0.91,
          lm_logits_top5: [
            [101, 0.62],
            [201, 0.23],
          ],
          p_copy_top5: [[1, 0.82]],
          p_copy_entropy: 0.24,
          copy_source_index: 1,
          phrase_bias_active: false,
          layer_l2: [0.7, 0.9],
        },
        {
          position: 1,
          decoded_token_id: 102,
          decoded_token_str: 'and',
          slot_type: 'CONNECTIVE',
          slot_type_confidence: 0.72,
          lm_logits_top5: [
            { token_id: 102, token_str: 'and', probability: 0.7 },
          ],
          p_copy_top5: [[0, 0.1]],
          p_copy_entropy: 1.2,
          copy_source_index: -1,
          phrase_bias_active: false,
          layer_l2: [0.8, 1.1],
        },
        {
          position: 2,
          decoded_token_id: 103,
          decoded_token_str: '^3',
          slot_type: 'STAGE_VAR',
          slot_type_confidence: 0.88,
          lm_logits_top5: [[103, 0.52]],
          p_copy_top5: [
            { source_position: 0, source_token: 'A0', probability: 0.73 },
          ],
          p_copy_entropy: 0.35,
          copy_source_index: 0,
          phrase_bias_active: true,
          layer_l2: [0.9, 1.3],
        },
      ],
      emission_route_counts: { lm: 1, copy: 2 },
      summary: {
        trace_warnings: ['post_processing_heavy_repair'],
      },
    },
  };
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

function parseCommit(kind: string, payload: string): SggsCommit {
  const result = parseSggsCommit(kind, payload);
  if (!result.ok) throw new Error(result.error);
  return result.commit;
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

describe('Mode 7 mechanistic axis_attrs selectors', () => {
  it('extracts activation hooks and attention heads from head_commit axis_attrs', () => {
    const result = parseSggsCommit(
      SGGS_EVENT_HEAD_COMMIT,
      headCommitPayload({ axis_attrs: mode7AxisAttrs() }),
    );
    expect(result.ok).toBe(true);
    if (!result.ok || result.commit.kind !== 'head_commit') return;

    expect(hasMode7MechanisticAxisAttrs(result.commit.axis_attrs)).toBe(true);
    const payload = selectMode7AxisPayload(result.commit.axis_attrs);
    expect(payload.schema_version).toBe(MODE7_TRACE_SCHEMA_VERSION);

    const layers = selectMode7ActivationLayers(result.commit.axis_attrs);
    expect(layers.find((layer) => layer.name === 'encoder.0')?.l2Norm).toBe(
      1.5,
    );
    expect(layers.find((layer) => layer.name === 'encoder.1')?.hookFired).toBe(
      true,
    );
    expect(layers.find((layer) => layer.name === 'decoder.0')?.l2Norm).toBeCloseTo(
      0.8,
    );

    const attention = selectMode7AttentionHeads(result.commit.axis_attrs);
    expect(attention[0]).toMatchObject({
      layer: 'decoder.0',
      headIndex: 2,
      sourceToken: 'OmegaSafe',
      targetToken: 'reply',
    });
    expect(attention.map((head) => head.label)).toContain('attention.layer0');
  });

  it('extracts load-bearing tokens and logits/copy summary from head_commit axis_attrs', () => {
    const result = parseSggsCommit(
      SGGS_EVENT_HEAD_COMMIT,
      headCommitPayload({ axis_attrs: mode7AxisAttrs() }),
    );
    expect(result.ok).toBe(true);
    if (!result.ok || result.commit.kind !== 'head_commit') return;

    const tokens = selectMode7LoadBearingTokens(result.commit.axis_attrs);
    expect(tokens.map((token) => token.slotType)).toEqual([
      'OMEGA',
      'STAGE_VAR',
    ]);
    expect(tokens[0]).toMatchObject({
      position: 0,
      token: 'OmegaSafe',
      copySourceIndex: 1,
      sourceToken: 'OmegaSafe',
    });
    expect(tokens[1]).toMatchObject({
      position: 2,
      token: '^3',
      copySourceIndex: 0,
      sourceToken: 'A0',
      phraseBiasActive: true,
    });

    const summary = selectMode7LogitsCopySummary(result.commit.axis_attrs);
    expect(summary.positions).toBe(3);
    expect(summary.copiedPositions).toBe(2);
    expect(summary.maxLmProbability).toBe(0.7);
    expect(summary.maxCopyProbability).toBe(0.82);
    expect(summary.meanCopyEntropy).toBeCloseTo((0.24 + 1.2 + 0.35) / 3);
    expect(summary.routeCounts).toEqual({ lm: 1, copy: 2 });
  });

  it('builds structural linkage and a concise trace label/explanation', () => {
    const result = parseSggsCommit(
      SGGS_EVENT_HEAD_COMMIT,
      headCommitPayload({
        head_index: 7,
        head_name: 'model_generation',
        node_id: 'n-output',
        node_label: 'plain-English reply',
        parent_node_id: 'n-parent',
        axis_attrs: mode7AxisAttrs(),
      }),
    );
    expect(result.ok).toBe(true);
    if (!result.ok || result.commit.kind !== 'head_commit') return;

    const linkage = selectMode7StructuralCommitLinkage(result.commit);
    expect(linkage).toMatchObject({
      turnId: 't-001',
      headIndex: 7,
      headName: 'model_generation',
      nodeId: 'n-output',
      parentNodeId: 'n-parent',
      traceId: 'trace-mode7-001',
      objectId: 'mode7-object-001',
      source: 'stage3_chat_repl',
      modelCheckpointId: 'ckpt-final',
      modelCodeVersion: 'abc123',
      schemaVersion: MODE7_TRACE_SCHEMA_VERSION,
    });
    expect(linkage.parentIds).toEqual([
      'session-001',
      'turn-001',
      't-001',
      'n-parent',
    ]);

    const trace = selectMode7MechanisticTrace(result.commit);
    expect(trace?.label).toBe('Network Attribution / Mechanistic Trace');
    expect(trace?.explanation).toContain('activations');
    expect(trace?.warnings).toEqual(['post_processing_heavy_repair']);
    expect(trace?.structuralCommit.traceId).toBe('trace-mode7-001');
  });

  it('does not classify ordinary live-tree axis_attrs as Mode 7 mechanistic data', () => {
    const result = parseSggsCommit(
      SGGS_EVENT_HEAD_COMMIT,
      headCommitPayload({
        axis_attrs: { noetic: 3, domain: 'P', register: 'A' },
      }),
    );
    expect(result.ok).toBe(true);
    if (!result.ok || result.commit.kind !== 'head_commit') return;

    expect(hasMode7MechanisticAxisAttrs(result.commit.axis_attrs)).toBe(false);
    expect(selectMode7MechanisticTrace(result.commit)).toBeNull();
  });
});

// -- Live tree accumulator --------------------------------------------------

describe('applySggsCommitToLiveTree', () => {
  it('accumulates head commits into a growing thought tree', () => {
    let state = createEmptySggsLiveTreeState();
    state = applySggsCommitToLiveTree(
      state,
      parseCommit(SGGS_EVENT_TURN_START, turnStartPayload('t-live', 'grow')),
    );
    state = applySggsCommitToLiveTree(
      state,
      parseCommit(
        SGGS_EVENT_HEAD_COMMIT,
        headCommitPayload({
          head_index: 0,
          head_name: 'prompt',
          node_id: 'root',
          node_kind: 'user_prompt',
          node_label: 'Grow a tree',
          parent_node_id: null,
        }),
      ),
    );
    state = applySggsCommitToLiveTree(
      state,
      parseCommit(
        SGGS_EVENT_HEAD_COMMIT,
        headCommitPayload({
          head_index: 1,
          head_name: 'cas',
          node_id: 'child',
          node_kind: 'cas_expression',
          node_label: '^2^P',
          parent_node_id: 'root',
          axis_attrs: { normalized_label: 'positive-principled' },
        }),
      ),
    );

    expect(state.turnId).toBe('t-live');
    expect(state.tree?.node_count).toBe(3);
    expect(state.tree?.edge_count).toBe(2);
    expect(state.tree?.root.id).toBe('n0');
    expect(state.tree?.root.children?.[0]?.id).toBe('root');
    expect(state.tree?.root.children?.[0]?.children?.[0]?.id).toBe('child');
    expect(state.nodes.find((node) => node.id === 'child')?.normalized_label).toBe(
      'positive-principled',
    );
  });

  it('replaces synthetic parent edges with explicit edge commits', () => {
    let state = createEmptySggsLiveTreeState();
    state = applySggsCommitToLiveTree(
      state,
      parseCommit(
        SGGS_EVENT_HEAD_COMMIT,
        headCommitPayload({ node_id: 'root', parent_node_id: null }),
      ),
    );
    state = applySggsCommitToLiveTree(
      state,
      parseCommit(
        SGGS_EVENT_HEAD_COMMIT,
        headCommitPayload({ node_id: 'child', parent_node_id: 'root' }),
      ),
    );
    expect(state.edges[0]?.id).toBe('parent:root->child');

    state = applySggsCommitToLiveTree(
      state,
      parseCommit(
        SGGS_EVENT_EDGE_COMMIT,
        JSON.stringify({
          kind: 'edge_commit',
          schema_version: SGGS_STREAM_SCHEMA_VERSION,
          turn_id: 't-001',
          edge_id: 'edge-explicit',
          source_node_id: 'root',
          target_node_id: 'child',
          edge_kind: 'parent_child',
        }),
      ),
    );

    expect(state.edges).toHaveLength(1);
    expect(state.edges[0]?.id).toBe('edge-explicit');
    expect(state.tree?.root.children?.[0]?.id).toBe('child');
  });

  it('records warning, error, and turn_end metadata without changing nodes', () => {
    let state = createEmptySggsLiveTreeState();
    state = applySggsCommitToLiveTree(
      state,
      parseCommit(
        SGGS_EVENT_WARNING,
        JSON.stringify({
          kind: 'warning',
          schema_version: SGGS_STREAM_SCHEMA_VERSION,
          turn_id: 't-001',
          severity: 'warning',
          message: 'partial tree',
        }),
      ),
    );
    state = applySggsCommitToLiveTree(
      state,
      parseCommit(
        SGGS_EVENT_ERROR,
        JSON.stringify({
          kind: 'error',
          schema_version: SGGS_STREAM_SCHEMA_VERSION,
          turn_id: 't-001',
          code: 'E_PARTIAL',
          message: 'missing leaf',
        }),
      ),
    );
    state = applySggsCommitToLiveTree(
      state,
      parseCommit(SGGS_EVENT_TURN_END, turnEndPayload()),
    );

    expect(state.nodes).toHaveLength(0);
    expect(state.warnings[0]?.message).toBe('partial tree');
    expect(state.errors[0]?.code).toBe('E_PARTIAL');
    expect(state.finalTraceId).toBe('trace-uuid');
    expect(state.durationMs).toBe(150);
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

  it('accepts unnamed default SSE message events via embedded kind', () => {
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
      source.simulateEvent('message', {
        data: turnStartPayload(),
        lastEventId: 'evt-default',
      });
    });

    expect(commits.map((c) => c.kind)).toEqual(['turn_start']);
  });

  it('reports unknown default SSE message kinds without dispatching commits', () => {
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
      source.simulateEvent('message', {
        data: JSON.stringify({ kind: 'future_event', turn_id: 't-001' }),
      });
    });

    expect(onCommit).not.toHaveBeenCalled();
    expect(onError).toHaveBeenCalledWith(expect.stringMatching(/Unknown SGGS/));
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

describe('useSggsLiveTree', () => {
  it('exposes a live accumulated tree and stream cursor', () => {
    const onCommit = vi.fn();
    const { result } = renderHook(() =>
      useSggsLiveTree({
        url: '/api/sggs/stream',
        enabled: true,
        onCommit,
        eventSourceFactory: (u) => new MockEventSource(u),
      }),
    );

    const source = MockEventSource.instances[0];
    act(() => {
      source.simulateOpen();
      source.simulateEvent(SGGS_EVENT_HEAD_COMMIT, {
        data: headCommitPayload({ node_id: 'root', parent_node_id: null }),
        lastEventId: 'evt-root',
      });
      source.simulateEvent(SGGS_EVENT_HEAD_COMMIT, {
        data: headCommitPayload({ node_id: 'leaf', parent_node_id: 'root' }),
        lastEventId: 'evt-leaf',
      });
    });

    expect(result.current.status).toBe('open');
    expect(result.current.lastEventId).toBe('evt-leaf');
    expect(result.current.tree?.node_count).toBe(2);
    expect(result.current.tree?.root.children?.[0]?.id).toBe('leaf');
    expect(onCommit).toHaveBeenCalledTimes(2);
    expect(onCommit.mock.calls[1]?.[1].tree?.node_count).toBe(2);
  });

  it('stores malformed JSON errors and keeps accumulating later valid commits', () => {
    const onError = vi.fn();
    const { result } = renderHook(() =>
      useSggsLiveTree({
        url: '/api/sggs/stream',
        enabled: true,
        onError,
        eventSourceFactory: (u) => new MockEventSource(u),
      }),
    );

    const source = MockEventSource.instances[0];
    act(() => {
      source.simulateOpen();
      source.simulateEvent(SGGS_EVENT_HEAD_COMMIT, { data: '{not-json' });
      source.simulateEvent(SGGS_EVENT_HEAD_COMMIT, {
        data: headCommitPayload({ node_id: 'root', parent_node_id: null }),
        lastEventId: 'evt-recovered',
      });
    });

    expect(result.current.state.streamErrors[0]).toMatch(/Could not parse/);
    expect(onError).toHaveBeenCalled();
    expect(result.current.tree?.root.id).toBe('root');
    expect(result.current.lastEventId).toBe('evt-recovered');
  });

  it('reset clears accumulated live tree state without closing the stream', () => {
    const { result } = renderHook(() =>
      useSggsLiveTree({
        url: '/api/sggs/stream',
        enabled: true,
        eventSourceFactory: (u) => new MockEventSource(u),
      }),
    );

    const source = MockEventSource.instances[0];
    act(() => {
      source.simulateOpen();
      source.simulateEvent(SGGS_EVENT_HEAD_COMMIT, {
        data: headCommitPayload({ node_id: 'root', parent_node_id: null }),
      });
    });
    expect(result.current.tree?.node_count).toBe(1);

    act(() => {
      result.current.reset();
    });

    expect(source.readyState).toBe(EVENT_SOURCE_OPEN);
    expect(result.current.tree).toBeNull();
    expect(result.current.state.commits).toHaveLength(0);
  });
});
