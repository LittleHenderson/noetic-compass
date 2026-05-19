/**
 * Tests for the CAS Verification Stack integration in the Atlas.
 *
 * Coverage (per the spec brief):
 *  1. Reviewer-Mode filter works — when toggled on, only nodes whose
 *     verification.decision === 'SUPPRESS' render.
 *  2. The Verification panel renders all four decision_tier colors
 *     correctly (high / medium / suppress / uncertain).
 *  3. Missing `verification` field doesn't crash existing trace rendering.
 *
 * Reserved language guard: the panel surfaces "accepted", "suppressed",
 * "decision_tier", and "suppression reasons" — never "rejected",
 * "failed", or "skipped" — so a snapshot-style assertion catches drift.
 */
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import {
  ThoughtTreeView,
  type ThoughtTree,
  type ThoughtTreeNode,
  type NodeVerification,
} from './ThoughtTreeView';
import { VerificationPanel } from './VerificationPanel';

// ── Builders ────────────────────────────────────────────────────────────────

function makeNode(
  id: string,
  label: string,
  verification?: NodeVerification,
  children?: ThoughtTreeNode[],
): ThoughtTreeNode {
  return {
    id,
    node_key: `cas_expression|${id}|${label}|`,
    kind: 'cas_expression',
    role: id,
    label,
    normalized_label: label.toLowerCase(),
    children,
    verification,
  };
}

function makeTree(nodes: ThoughtTreeNode[]): ThoughtTree {
  // Build a synthetic linear tree: root → n1 → n2 → n3 → …
  const flat = nodes;
  const edges = flat.slice(1).map((n, i) => ({
    id: `e${i}`,
    edge_key: `${flat[i].id}->${n.id}`,
    source: flat[i].id,
    target: n.id,
    source_key: flat[i].id,
    target_key: n.id,
    kind: 'parent_child',
  }));
  // Build nested children so the layout walks the whole tree.
  for (let i = 0; i < flat.length - 1; i++) {
    flat[i].children = [flat[i + 1]];
  }
  return {
    root: flat[0],
    nodes: flat,
    edges,
    node_count: flat.length,
    edge_count: edges.length,
  };
}

/** Helper that mirrors the IdeaAtlasPage Reviewer-Mode filter logic. */
function reviewerFilterTree(tree: ThoughtTree): ThoughtTree {
  const suppressed = tree.nodes.filter(
    (n) => n.verification?.decision === 'SUPPRESS',
  );
  const ids = new Set(suppressed.map((n) => n.id));
  const edges = tree.edges.filter(
    (e) => ids.has(e.source) && ids.has(e.target),
  );
  const root: ThoughtTreeNode = {
    id: '__reviewer_mode_root__',
    node_key: '__reviewer_mode_root__',
    kind: 'user_prompt',
    role: 'reviewer_mode',
    label: 'Reviewer Mode — suppressed nodes only',
    normalized_label: 'reviewer mode — suppressed nodes only',
    children: suppressed.map((n) => ({ ...n, children: [] })),
  };
  return {
    root,
    nodes: suppressed,
    edges,
    node_count: suppressed.length,
    edge_count: edges.length,
  };
}

// ── 1. Reviewer-Mode filter ─────────────────────────────────────────────────

describe('Reviewer Mode — suppressed-only filter', () => {
  it('renders every node when reviewer mode is off', () => {
    const tree = makeTree([
      makeNode('n0', 'root'),
      makeNode('n1', 'accept-high', {
        decision: 'ACCEPT',
        decision_tier: 'high',
        ensemble_agreement: true,
        confidence: 0.95,
      }),
      makeNode('n2', 'suppress-one', {
        decision: 'SUPPRESS',
        decision_tier: 'suppress',
        suppression_reasons: ['ensemble_all_disagree'],
      }),
      makeNode('n3', 'accept-medium', {
        decision: 'ACCEPT',
        decision_tier: 'medium',
        ensemble_agreement: true,
        confidence: 0.7,
      }),
    ]);
    render(<ThoughtTreeView tree={tree} />);
    // All four nodes should render their data-node-id surfaces.
    expect(
      document.querySelectorAll('[data-testid^="thought-tree-node-"]').length,
    ).toBe(4);
  });

  it('renders only SUPPRESS nodes when reviewer mode is on', () => {
    const fullTree = makeTree([
      makeNode('n0', 'root'),
      makeNode('n1', 'accept-high', {
        decision: 'ACCEPT',
        decision_tier: 'high',
      }),
      makeNode('n2', 'suppress-one', {
        decision: 'SUPPRESS',
        decision_tier: 'suppress',
        suppression_reasons: ['ensemble_all_disagree'],
      }),
      makeNode('n3', 'accept-medium', {
        decision: 'ACCEPT',
        decision_tier: 'medium',
      }),
      makeNode('n4', 'suppress-two', {
        decision: 'SUPPRESS',
        decision_tier: 'suppress',
        suppression_reasons: ['trace_unstable'],
      }),
    ]);
    const filtered = reviewerFilterTree(fullTree);
    render(<ThoughtTreeView tree={filtered} />);
    // Two suppressed nodes survive (n2, n4); the others are filtered out.
    expect(document.querySelector('[data-testid="thought-tree-node-n2"]'))
      .not.toBeNull();
    expect(document.querySelector('[data-testid="thought-tree-node-n4"]'))
      .not.toBeNull();
    expect(document.querySelector('[data-testid="thought-tree-node-n1"]'))
      .toBeNull();
    expect(document.querySelector('[data-testid="thought-tree-node-n3"]'))
      .toBeNull();
  });
});

// ── 2. Verification panel — all four decision_tier colors ───────────────────

describe('VerificationPanel — decision_tier color coding', () => {
  it('renders the HIGH (accept, green) tier with confidence + ensemble', () => {
    render(
      <VerificationPanel
        verification={{
          decision: 'ACCEPT',
          decision_tier: 'high',
          ensemble_agreement: true,
          confidence: 0.94,
        }}
      />,
    );
    const panel = screen.getByTestId('verification-panel');
    expect(panel.getAttribute('data-decision-tier')).toBe('high');
    expect(panel.getAttribute('data-decision')).toBe('ACCEPT');
    const badge = screen.getByTestId('verification-tier-badge');
    expect(badge.textContent).toBe('HIGH');
    // Green palette
    expect(badge.className).toContain('emerald');
    expect(screen.getByTestId('verification-confidence').textContent)
      .toContain('0.94');
    expect(screen.getByTestId('verification-ensemble-agreement').textContent)
      .toBe('true');
    // Reserved-language guard
    expect(screen.getByTestId('verification-decision').textContent)
      .toBe('accepted');
  });

  it('renders the MEDIUM (accept, yellow) tier', () => {
    render(
      <VerificationPanel
        verification={{
          decision: 'ACCEPT',
          decision_tier: 'medium',
          ensemble_agreement: true,
          confidence: 0.71,
        }}
      />,
    );
    const panel = screen.getByTestId('verification-panel');
    expect(panel.getAttribute('data-decision-tier')).toBe('medium');
    const badge = screen.getByTestId('verification-tier-badge');
    expect(badge.textContent).toBe('MEDIUM');
    // Yellow palette
    expect(badge.className).toContain('amber');
  });

  it('renders the SUPPRESS (red) tier with suppression_reasons chips', () => {
    render(
      <VerificationPanel
        verification={{
          decision: 'SUPPRESS',
          decision_tier: 'suppress',
          ensemble_agreement: false,
          suppression_reasons: [
            'final_token_conflicted',
            'focus_token_conflicted',
            'mean_over_seq_len_conflicted',
          ],
        }}
      />,
    );
    const panel = screen.getByTestId('verification-panel');
    expect(panel.getAttribute('data-decision-tier')).toBe('suppress');
    expect(panel.getAttribute('data-decision')).toBe('SUPPRESS');
    const badge = screen.getByTestId('verification-tier-badge');
    expect(badge.textContent).toBe('SUPPRESS');
    // Red palette
    expect(badge.className).toContain('rose');
    // All three reason chips render
    const chips = screen.getAllByTestId('verification-suppression-chip');
    expect(chips.length).toBe(3);
    const reasonAttrs = chips.map((c) => c.getAttribute('data-reason'));
    expect(reasonAttrs).toContain('final_token_conflicted');
    expect(reasonAttrs).toContain('focus_token_conflicted');
    expect(reasonAttrs).toContain('mean_over_seq_len_conflicted');
    // Reserved-language guard
    expect(screen.getByTestId('verification-decision').textContent)
      .toBe('suppressed');
  });

  it('renders the UNCERTAIN (gray) tier when no verdict is rendered', () => {
    render(
      <VerificationPanel
        verification={{
          decision: null,
          decision_tier: 'uncertain',
        }}
      />,
    );
    const panel = screen.getByTestId('verification-panel');
    expect(panel.getAttribute('data-decision-tier')).toBe('uncertain');
    const badge = screen.getByTestId('verification-tier-badge');
    expect(badge.textContent).toBe('UNCERTAIN');
    // Gray palette
    expect(badge.className).toContain('slate');
    expect(screen.getByTestId('verification-decision').textContent)
      .toBe('no verdict');
  });

  it('falls back to UNCERTAIN when decision_tier is omitted entirely', () => {
    render(
      <VerificationPanel
        verification={{
          decision: null,
        }}
      />,
    );
    const badge = screen.getByTestId('verification-tier-badge');
    expect(badge.textContent).toBe('UNCERTAIN');
  });
});

// ── 3. Missing verification doesn't break existing rendering ────────────────

describe('Missing verification field — backward compatibility', () => {
  it('VerificationPanel renders nothing when verification is null', () => {
    const { container } = render(
      <VerificationPanel verification={null} />,
    );
    expect(container.firstChild).toBeNull();
  });

  it('VerificationPanel renders nothing when verification is undefined', () => {
    const { container } = render(
      <VerificationPanel verification={undefined} />,
    );
    expect(container.firstChild).toBeNull();
  });

  it('ThoughtTreeView renders nodes that have no verification field', () => {
    // Tree where no node has the new verification field — mirrors a
    // pre-Stack v0 trace. Must not crash and must render every node.
    const tree = makeTree([
      makeNode('n0', 'root'),
      makeNode('n1', 'one'),
      makeNode('n2', 'two'),
    ]);
    render(<ThoughtTreeView tree={tree} />);
    expect(
      document.querySelectorAll('[data-testid^="thought-tree-node-"]').length,
    ).toBe(3);
  });
});
