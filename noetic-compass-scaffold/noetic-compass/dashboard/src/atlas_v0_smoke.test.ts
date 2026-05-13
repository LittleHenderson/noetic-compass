/**
 * Atlas v0 end-to-end smoke (Codex guardrails 4d3216f #6, a658f6d).
 *
 * Pins the REPL → cas atlas-save → TraceLoader.validateAtlasTrace
 * contract against a stable committed fixture so the smoke runs in
 * any environment without needing a live Python REPL.
 *
 * The fixture at `src/__fixtures__/trace_thought_becoming_action.json`
 * was produced by:
 *
 *   printf "explain a thought becoming action\n/trace\n/quit\n" \
 *     | python inference/cas_cli.py chat-stage3 \
 *     | awk '/^{$/,/^}$/' > raw.json
 *   python inference/cas_cli.py atlas-save \
 *     --from raw.json --out-dir out --validate-strict
 *
 * then `trace_id` + `created_at` were normalized to fixed values for
 * determinism. Everything else is exactly what the live pipeline
 * emitted on 2026-05-13.
 */
import { describe, expect, it } from 'vitest';
import fixture from './__fixtures__/trace_thought_becoming_action.json';
import { isAtlasTrace, validateAtlasTrace } from './lib/trace';

describe('Atlas v0 end-to-end smoke', () => {
  it('committed REPL fixture passes the strict validator', () => {
    expect(isAtlasTrace(fixture)).toBe(true);
    const result = validateAtlasTrace(fixture);
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    // Schema version pinned
    expect(result.trace.schema_version).toBe('traceability_v0');
    // Exact node + edge counts from the live pipeline run that
    // produced this fixture. Surfacing this in the inbox claim was
    // overstated previously (Codex audit a658f6d non-blocker note) —
    // these are now hard assertions, not soft checks.
    expect(result.trace.thought_tree.node_count).toBe(4);
    expect(result.trace.thought_tree.edge_count).toBe(3);
    expect(result.trace.thought_tree.nodes).toHaveLength(4);
    expect(result.trace.thought_tree.edges).toHaveLength(3);
    // NL bridge path was exercised
    expect(result.trace.input.input_kind).toBe('nl_bridge');
    if (result.trace.input.input_kind === 'nl_bridge') {
      expect(result.trace.input.user_text).toBe(
        'explain a thought becoming action',
      );
      expect(result.trace.input.nl_bridge.matched_pattern).toBe(
        'thought becoming action',
      );
      expect(result.trace.input.nl_bridge.inferred_cas_expression).toBe(
        '^9^O',
      );
    }
    // Every edge resolves to a real node (no danglers — would fail
    // the validator anyway, but explicit assertion for clarity).
    const nodeIds = new Set(result.trace.thought_tree.nodes.map((n) => n.id));
    for (const edge of result.trace.thought_tree.edges) {
      expect(nodeIds.has(edge.source)).toBe(true);
      expect(nodeIds.has(edge.target)).toBe(true);
    }
  });

  it('mutated fixture (dangling edge) is rejected by the tightened validator', () => {
    // Codex audit a658f6d blocker 1 regression pin: validator must
    // catch an edge whose target is not a real node id.
    const mutated = JSON.parse(JSON.stringify(fixture));
    mutated.thought_tree.edges[0].target = 'nonexistent_node';
    const result = validateAtlasTrace(mutated);
    expect(result.ok).toBe(false);
  });
});
