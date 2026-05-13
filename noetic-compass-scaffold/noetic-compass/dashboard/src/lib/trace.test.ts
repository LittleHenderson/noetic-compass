/**
 * Tests for `lib/trace.ts` — the TS validator for the traceability_v0
 * JSON schema. These tests pin the Python-side schema to TS by checking:
 *   - a valid trace round-trips through the validator
 *   - each required top-level key is required (omit one → reject)
 *   - schema_version mismatches reject
 *   - the discriminated input union rejects malformed members
 */

import { describe, it, expect } from 'vitest';
import {
  type AtlasTrace,
  REQUIRED_TRACE_KEYS,
  TRACE_SCHEMA_VERSION,
  isAtlasTrace,
  validateAtlasTrace,
} from './trace';

// A canonical, fully-valid trace — used as the baseline that every
// removal test starts from. Shape mirrors what `build_v0_trace` emits.
function makeValidTrace(): AtlasTrace {
  return {
    schema_version: TRACE_SCHEMA_VERSION,
    trace_id: '11111111-2222-3333-4444-555555555555',
    created_at: '2026-05-13T17:30:00Z',
    input: {
      input_kind: 'cas_expression',
      cas_expression: '^9^O',
      source_tokens: [{ index: 0, token: '^9^O' }],
    },
    output: {
      english: 'A Below/Effect in the Operational domain.',
      n_tokens: 8,
    },
    copy: {
      copied_identifiers: [],
      missed_identifiers: [],
      coverage: null,
      per_identifier: [],
    },
    slot_trace: {
      length: 8,
      slot_counts_by_label: { 'joining word': 8 },
      longest_stage_var_run: 0,
      raw_trace: null,
    },
    confidence: {
      qualitative_coverage: 'strong',
      slot_quality: 'only joining words generated',
      caveats: [],
      warning_flags: [],
    },
    thought_tree: {
      root: {
        kind: 'user_prompt',
        role: 'input',
        label: '^9^O',
        normalized_label: '^9^o',
        text: '^9^O',
        children: [],
      },
      nodes: [
        {
          id: 'n0',
          node_key: 'user_prompt|input|^9^o|',
          kind: 'user_prompt',
          role: 'input',
          label: '^9^O',
          normalized_label: '^9^o',
          text: '^9^O',
        },
      ],
      edges: [],
      node_count: 1,
      edge_count: 0,
    },
  };
}

describe('isAtlasTrace', () => {
  it('accepts a fully-valid v0 trace', () => {
    expect(isAtlasTrace(makeValidTrace())).toBe(true);
  });

  it('rejects null / undefined / primitives / arrays', () => {
    expect(isAtlasTrace(null)).toBe(false);
    expect(isAtlasTrace(undefined)).toBe(false);
    expect(isAtlasTrace(42)).toBe(false);
    expect(isAtlasTrace('not a trace')).toBe(false);
    expect(isAtlasTrace([])).toBe(false);
  });

  it('rejects when schema_version is wrong', () => {
    const t: Record<string, unknown> = {
      ...(makeValidTrace() as unknown as Record<string, unknown>),
    };
    t.schema_version = 'trace_v0';
    expect(isAtlasTrace(t)).toBe(false);
  });

  it('rejects when each required top-level key is missing', () => {
    for (const key of REQUIRED_TRACE_KEYS) {
      const t: Record<string, unknown> = {
        ...(makeValidTrace() as unknown as Record<string, unknown>),
      };
      delete t[key];
      expect(isAtlasTrace(t)).toBe(false);
    }
  });

  it('accepts an nl_bridge input variant', () => {
    const t = makeValidTrace();
    t.input = {
      input_kind: 'nl_bridge',
      user_text: 'explain a thought becoming action',
      cas_expression: '^9^O',
      source_tokens: [{ index: 0, token: '^9^O' }],
      nl_bridge: {
        matched_pattern: 'thought becoming action',
        confidence: 0.95,
        rationale: 'Below/Effect in the Operational domain.',
        inferred_cas_expression: '^9^O',
      },
    };
    expect(isAtlasTrace(t)).toBe(true);
  });

  it('rejects an nl_bridge variant missing the nl_bridge sub-dict', () => {
    const t = makeValidTrace();
    // Cast through unknown so we can construct the malformed shape
    t.input = {
      input_kind: 'nl_bridge',
      user_text: 'x',
      cas_expression: '^9^O',
      source_tokens: [{ index: 0, token: '^9^O' }],
      // nl_bridge intentionally omitted
    } as unknown as AtlasTrace['input'];
    expect(isAtlasTrace(t)).toBe(false);
  });

  it('rejects when source_tokens are bare strings instead of objects', () => {
    const t = makeValidTrace();
    (t.input as unknown as Record<string, unknown>).source_tokens = ['^9^O'];
    expect(isAtlasTrace(t)).toBe(false);
  });

  it('rejects when warning_flags has an invalid severity', () => {
    const t = makeValidTrace();
    t.confidence.warning_flags = [
      // @ts-expect-error invalid severity intentional for test
      { kind: 'bad', severity: 'critical', message: 'nope' },
    ];
    expect(isAtlasTrace(t)).toBe(false);
  });

  it('round-trips through JSON.stringify/parse', () => {
    const t = makeValidTrace();
    const reloaded = JSON.parse(JSON.stringify(t));
    expect(isAtlasTrace(reloaded)).toBe(true);
  });
});

describe('validateAtlasTrace', () => {
  it('returns ok=true with the narrowed trace on success', () => {
    const result = validateAtlasTrace(makeValidTrace());
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.trace.schema_version).toBe(TRACE_SCHEMA_VERSION);
    }
  });

  it('returns ok=false with a schema_version message on bad version', () => {
    const t: Record<string, unknown> = {
      ...(makeValidTrace() as unknown as Record<string, unknown>),
    };
    t.schema_version = 'trace_v0';
    const result = validateAtlasTrace(t);
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.error.toLowerCase()).toContain('schema_version');
    }
  });

  it('reports the missing key in the error message', () => {
    const t: Record<string, unknown> = {
      ...(makeValidTrace() as unknown as Record<string, unknown>),
    };
    delete t.thought_tree;
    const result = validateAtlasTrace(t);
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.error).toContain('thought_tree');
    }
  });
});

// ---------------------------------------------------------------------
// REGRESSION PIN (Codex audit a658f6d blocker 1): per-node + per-edge
// identity checks. The validator must reject:
//   - any node missing string id / node_key / kind / role / label /
//     normalized_label
//   - any edge missing string id / edge_key / source / target /
//     source_key / target_key / kind
//   - any edge whose source or target does not exist in the node id set
//   - thought_tree where node_count or edge_count disagrees with the
//     flat array length
// ---------------------------------------------------------------------

function makeTreeWithTwoNodes(): AtlasTrace {
  const t = makeValidTrace();
  t.thought_tree = {
    root: {
      id: 'n0',
      node_key: 'user_prompt|input|^9^o|',
      kind: 'user_prompt',
      role: 'input',
      label: '^9^O',
      normalized_label: '^9^o',
      text: '^9^O',
      children: [],
    },
    nodes: [
      {
        id: 'n0',
        node_key: 'user_prompt|input|^9^o|',
        kind: 'user_prompt',
        role: 'input',
        label: '^9^O',
        normalized_label: '^9^o',
      },
      {
        id: 'n1',
        node_key: 'model_generation|output|thought becoming action|',
        kind: 'model_generation',
        role: 'output',
        label: 'thought becoming action',
        normalized_label: 'thought becoming action',
      },
    ],
    edges: [
      {
        id: 'e0',
        edge_key:
          'user_prompt|input|^9^o||model_generation|output|thought becoming action||parent_child|',
        source: 'n0',
        target: 'n1',
        source_key: 'user_prompt|input|^9^o|',
        target_key: 'model_generation|output|thought becoming action|',
        kind: 'parent_child',
      },
    ],
    node_count: 2,
    edge_count: 1,
  };
  return t;
}

describe('validateAtlasTrace — thought_tree identity', () => {
  it('accepts a tree with full node + edge identity', () => {
    const result = validateAtlasTrace(makeTreeWithTwoNodes());
    expect(result.ok).toBe(true);
  });

  it('rejects a node missing node_key', () => {
    const t = makeTreeWithTwoNodes();
    delete (t.thought_tree.nodes[0] as unknown as Record<string, unknown>).node_key;
    const result = validateAtlasTrace(t);
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.error).toContain('node_key');
    }
  });

  it('rejects a node missing id', () => {
    const t = makeTreeWithTwoNodes();
    delete (t.thought_tree.nodes[1] as unknown as Record<string, unknown>).id;
    const result = validateAtlasTrace(t);
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.error).toContain('id');
    }
  });

  it('rejects each required string node field individually', () => {
    const fields = ['kind', 'role', 'label', 'normalized_label'] as const;
    for (const field of fields) {
      const t = makeTreeWithTwoNodes();
      delete (t.thought_tree.nodes[0] as unknown as Record<string, unknown>)[field as string];
      const result = validateAtlasTrace(t);
      expect(result.ok, `missing ${field}`).toBe(false);
      if (!result.ok) {
        expect(result.error).toContain(field);
      }
    }
  });

  it('rejects an edge missing edge_key', () => {
    const t = makeTreeWithTwoNodes();
    delete (t.thought_tree.edges[0] as unknown as Record<string, unknown>).edge_key;
    const result = validateAtlasTrace(t);
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.error).toContain('edge_key');
    }
  });

  it('rejects each required string edge field individually', () => {
    const fields = [
      'id',
      'source',
      'target',
      'source_key',
      'target_key',
      'kind',
    ] as const;
    for (const field of fields) {
      const t = makeTreeWithTwoNodes();
      delete (t.thought_tree.edges[0] as unknown as Record<string, unknown>)[field as string];
      const result = validateAtlasTrace(t);
      expect(result.ok, `missing ${field}`).toBe(false);
      if (!result.ok) {
        expect(result.error).toContain(field);
      }
    }
  });

  it('rejects an edge whose source is not a node id (dangling)', () => {
    const t = makeTreeWithTwoNodes();
    t.thought_tree.edges[0].source = 'nonexistent';
    const result = validateAtlasTrace(t);
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.error.toLowerCase()).toContain('source');
      expect(result.error).toContain('nonexistent');
    }
  });

  it('rejects an edge whose target is not a node id (dangling)', () => {
    const t = makeTreeWithTwoNodes();
    t.thought_tree.edges[0].target = 'phantom';
    const result = validateAtlasTrace(t);
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.error.toLowerCase()).toContain('target');
      expect(result.error).toContain('phantom');
    }
  });

  it('rejects node_count that disagrees with nodes.length', () => {
    const t = makeTreeWithTwoNodes();
    t.thought_tree.node_count = 5;
    const result = validateAtlasTrace(t);
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.error).toContain('node_count');
    }
  });

  it('rejects edge_count that disagrees with edges.length', () => {
    const t = makeTreeWithTwoNodes();
    t.thought_tree.edge_count = 99;
    const result = validateAtlasTrace(t);
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.error).toContain('edge_count');
    }
  });
});
