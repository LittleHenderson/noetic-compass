/**
 * Tests for ThoughtTreeView — Atlas v0 SVG renderer.
 *
 * Coverage (matches task brief):
 * - Renders the right number of nodes + edges from a sample tree
 * - Each node has accessible aria-label = node.label
 * - Click a node fires onNodeClick(node) with the right node
 * - selectedNodeId highlights only that node
 * - Empty tree renders the empty-state card
 * - Each supported kind renders with its own data-kind class
 * - Unknown kind falls back gracefully (slate color, no crash)
 *
 * Test trees mirror the JSON shape emitted by
 * `cas-native/inference/thought_tree.py::build_thought_tree`.
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import {
  ThoughtTreeView,
  type ThoughtTree,
  type ThoughtTreeNode,
  type ThoughtTreeEdge,
} from './ThoughtTreeView';

// ── Test data builders ─────────────────────────────────────────────────────

function node(
  id: string,
  kind: string,
  label: string,
  role: string = '',
  children?: ThoughtTreeNode[],
): ThoughtTreeNode {
  return {
    id,
    node_key: `${kind}|${role}|${label.toLowerCase()}|`,
    kind,
    role,
    label,
    normalized_label: label.toLowerCase(),
    children,
  };
}

function edge(id: string, source: string, target: string): ThoughtTreeEdge {
  return {
    id,
    edge_key: `${source}->${target}`,
    source,
    target,
    source_key: source,
    target_key: target,
    kind: 'parent_child',
  };
}

/** Build a tree that mirrors a real cas-explain trace shape. */
function makeSampleTree(): ThoughtTree {
  const ident1 = node('n2', 'identifier_attempt', 'stageA0_4_857', 'copied');
  const ident2 = node('n3', 'identifier_attempt', 'stageD3_4_857', 'missed');
  const slot = node('n4', 'slot_pattern', 'recognized 1 identifier position(s)', 'summary');
  const conf = node('n5', 'confidence_marker', 'coverage: weak — caveat present', 'weak');
  const gen = node('n1', 'model_generation', 'stub answer', 'output', [
    ident1,
    ident2,
    slot,
    conf,
  ]);
  const root = node('n0', 'user_prompt', '^7^P_{F5}', 'input', [gen]);

  const flat: ThoughtTreeNode[] = [root, gen, ident1, ident2, slot, conf];
  const edges: ThoughtTreeEdge[] = [
    edge('e0', 'n0', 'n1'),
    edge('e1', 'n1', 'n2'),
    edge('e2', 'n1', 'n3'),
    edge('e3', 'n1', 'n4'),
    edge('e4', 'n1', 'n5'),
  ];

  return {
    root,
    nodes: flat,
    edges,
    node_count: flat.length,
    edge_count: edges.length,
  };
}

/** Minimal tree with one nl_bridge node — exercises the future-NL-bridge path. */
function makeNlBridgeTree(): ThoughtTree {
  const bridge = node('n1', 'nl_bridge', 'thought becoming action', 'pattern');
  const root = node('n0', 'user_prompt', 'explain a thought becoming action', 'input', [bridge]);
  const flat = [root, bridge];
  const edges = [edge('e0', 'n0', 'n1')];
  return {
    root,
    nodes: flat,
    edges,
    node_count: flat.length,
    edge_count: edges.length,
  };
}

/** Empty tree — used to assert the empty-state card renders. */
const EMPTY_TREE: ThoughtTree = {
  root: {} as ThoughtTreeNode,
  nodes: [],
  edges: [],
  node_count: 0,
  edge_count: 0,
};

// ── Tests ─────────────────────────────────────────────────────────────────

describe('ThoughtTreeView — rendering', () => {
  it('renders the right number of nodes and edges from a sample tree', () => {
    const tree = makeSampleTree();
    const { container } = render(<ThoughtTreeView tree={tree} />);
    const nodeGroups = container.querySelectorAll('[data-node-id]');
    const edgePaths = container.querySelectorAll('[data-edge-id]');
    expect(nodeGroups.length).toBe(tree.nodes.length);
    expect(edgePaths.length).toBe(tree.edges.length);
  });

  it('each node has an aria-label equal to node.label', () => {
    const tree = makeSampleTree();
    render(<ThoughtTreeView tree={tree} />);
    for (const n of tree.nodes) {
      const el = screen.getByLabelText(n.label);
      expect(el).toBeInTheDocument();
      expect(el.getAttribute('data-node-id')).toBe(n.id);
    }
  });
});

describe('ThoughtTreeView — interaction', () => {
  it('clicking a node fires onNodeClick with that node', () => {
    const tree = makeSampleTree();
    const onNodeClick = vi.fn();
    render(<ThoughtTreeView tree={tree} onNodeClick={onNodeClick} />);
    const target = tree.nodes[2]; // first identifier_attempt
    const el = screen.getByLabelText(target.label);
    fireEvent.click(el);
    expect(onNodeClick).toHaveBeenCalledTimes(1);
    expect(onNodeClick).toHaveBeenCalledWith(target);
  });

  it('pressing Enter on a focused node also fires onNodeClick', () => {
    const tree = makeSampleTree();
    const onNodeClick = vi.fn();
    render(<ThoughtTreeView tree={tree} onNodeClick={onNodeClick} />);
    const target = tree.nodes[1]; // model_generation
    const el = screen.getByLabelText(target.label);
    fireEvent.keyDown(el, { key: 'Enter' });
    expect(onNodeClick).toHaveBeenCalledWith(target);
  });

  it('selectedNodeId marks exactly one node as selected', () => {
    const tree = makeSampleTree();
    const selectedId = 'n2';
    const { container } = render(
      <ThoughtTreeView tree={tree} selectedNodeId={selectedId} />,
    );
    const selected = container.querySelectorAll('[data-selected="true"]');
    expect(selected.length).toBe(1);
    expect(selected[0].getAttribute('data-node-id')).toBe(selectedId);
  });

  it('selectedNodeId=null marks no node as selected', () => {
    const tree = makeSampleTree();
    const { container } = render(
      <ThoughtTreeView tree={tree} selectedNodeId={null} />,
    );
    const selected = container.querySelectorAll('[data-selected="true"]');
    expect(selected.length).toBe(0);
  });
});

describe('ThoughtTreeView — empty state', () => {
  it('renders the empty-state card when node_count === 0', () => {
    render(<ThoughtTreeView tree={EMPTY_TREE} />);
    expect(screen.getByTestId('thought-tree-empty')).toBeInTheDocument();
    expect(screen.getByText(/Load a trace/i)).toBeInTheDocument();
  });

  it('does not render the SVG tree when empty', () => {
    const { container } = render(<ThoughtTreeView tree={EMPTY_TREE} />);
    expect(container.querySelector('[data-testid="thought-tree-view"]')).toBeNull();
    expect(container.querySelector('[data-node-id]')).toBeNull();
  });
});

describe('ThoughtTreeView — kind colors', () => {
  const SUPPORTED_KINDS = [
    'user_prompt',
    'cas_expression',
    'model_generation',
    'identifier_attempt',
    'slot_pattern',
    'confidence_marker',
    'nl_bridge',
  ] as const;

  it('each supported kind renders with data-kind set to its kind', () => {
    // Build a tree with one node per supported kind so a single render
    // exercises every palette entry.
    const children: ThoughtTreeNode[] = [
      node('n2', 'identifier_attempt', 'identA', 'copied'),
      node('n3', 'slot_pattern', 'pattern', 'summary'),
      node('n4', 'confidence_marker', 'coverage: weak', 'weak'),
      node('n5', 'nl_bridge', 'a bridge phrase', 'pattern'),
      node('n6', 'cas_expression', '^9^O', 'inferred'),
    ];
    const gen = node('n1', 'model_generation', 'output text', 'output', children);
    const root = node('n0', 'user_prompt', 'cas expr', 'input', [gen]);
    const flat = [root, gen, ...children];
    const edges = [
      edge('e0', 'n0', 'n1'),
      edge('e1', 'n1', 'n2'),
      edge('e2', 'n1', 'n3'),
      edge('e3', 'n1', 'n4'),
      edge('e4', 'n1', 'n5'),
      edge('e5', 'n1', 'n6'),
    ];
    const tree: ThoughtTree = {
      root,
      nodes: flat,
      edges,
      node_count: flat.length,
      edge_count: edges.length,
    };
    const { container } = render(<ThoughtTreeView tree={tree} />);
    for (const kind of SUPPORTED_KINDS) {
      const el = container.querySelector(`[data-kind="${kind}"]`);
      expect(el, `expected node with data-kind="${kind}"`).not.toBeNull();
    }
  });

  it('unknown kind falls back to data-kind="unknown" without crashing', () => {
    const stray = node('n1', 'totally_made_up_kind', 'mystery', 'role');
    const root = node('n0', 'user_prompt', 'cas expr', 'input', [stray]);
    const tree: ThoughtTree = {
      root,
      nodes: [root, stray],
      edges: [edge('e0', 'n0', 'n1')],
      node_count: 2,
      edge_count: 1,
    };
    const { container } = render(<ThoughtTreeView tree={tree} />);
    const el = container.querySelector('[data-node-id="n1"]');
    expect(el).not.toBeNull();
    expect(el?.getAttribute('data-kind')).toBe('unknown');
  });

  it('nl_bridge node renders with its own kind color slot even when no other nodes have it', () => {
    const tree = makeNlBridgeTree();
    const { container } = render(<ThoughtTreeView tree={tree} />);
    const bridge = container.querySelector('[data-node-id="n1"]');
    expect(bridge?.getAttribute('data-kind')).toBe('nl_bridge');
  });
});

describe('ThoughtTreeView — accessibility', () => {
  it('renders a tree role on the SVG container', () => {
    const tree = makeSampleTree();
    render(<ThoughtTreeView tree={tree} />);
    expect(screen.getByRole('tree', { name: /Thought Tree/i })).toBeInTheDocument();
  });

  it('every node is a treeitem with tabIndex=0', () => {
    const tree = makeSampleTree();
    const { container } = render(<ThoughtTreeView tree={tree} />);
    const items = container.querySelectorAll('[role="treeitem"]');
    expect(items.length).toBe(tree.nodes.length);
    for (const it of items) {
      expect(it.getAttribute('tabindex')).toBe('0');
    }
  });
});

describe('ThoughtTreeView — labels', () => {
  it('long labels are wrapped+truncated in the visible <text> but full label stays in aria-label', () => {
    const longLabel = 'a'.repeat(80);
    const child = node('n1', 'model_generation', longLabel, 'output');
    const root = node('n0', 'user_prompt', 'short label', 'input', [child]);
    const tree: ThoughtTree = {
      root,
      nodes: [root, child],
      edges: [edge('e0', 'n0', 'n1')],
      node_count: 2,
      edge_count: 1,
    };
    const { container } = render(<ThoughtTreeView tree={tree} />);
    const el = container.querySelector('[data-node-id="n1"]');
    expect(el?.getAttribute('aria-label')).toBe(longLabel);
    // Title is wrapped across up to 2 tspans on the title <text>; the
    // last tspan ends with an ellipsis when the label exceeds the
    // two-line budget. The kind chip's <text> is separate — we want
    // the title text, which is the <text> with multiple tspans.
    const titleTextEl = el && Array.from(el.querySelectorAll('text')).find(
      (t) => t.querySelectorAll('tspan').length >= 1,
    );
    expect(titleTextEl).toBeTruthy();
    expect(titleTextEl?.textContent?.endsWith('…')).toBe(true);
    // Visible title content must be strictly less than the full label.
    expect(
      (titleTextEl?.textContent ?? '').length,
    ).toBeLessThan(longLabel.length);
  });

  it('multi-word labels wrap to multiple lines as tspans', () => {
    // REGRESSION PIN (Codex audit 2026-05-13 visual polish): cards are
    // thought cards with wrapped titles, not single-line chips.
    const wrappingLabel =
      'A multi-word label that should clearly wrap onto two visible lines';
    const child = node('n1', 'model_generation', wrappingLabel, 'output');
    const root = node('n0', 'user_prompt', 'root', 'input', [child]);
    const tree: ThoughtTree = {
      root,
      nodes: [root, child],
      edges: [edge('e0', 'n0', 'n1')],
      node_count: 2,
      edge_count: 1,
    };
    const { container } = render(<ThoughtTreeView tree={tree} />);
    const el = container.querySelector('[data-node-id="n1"]');
    const titleTextEl = el && Array.from(el.querySelectorAll('text')).find(
      (t) => t.querySelectorAll('tspan').length >= 2,
    );
    expect(titleTextEl).toBeTruthy();
  });

  it('renders a kind chip with the human-readable kind label', () => {
    // REGRESSION PIN (Codex audit 2026-05-13 visual polish): cards
    // carry a small uppercase kind chip so stakeholders see what the
    // node IS, not just what it says.
    const root = node('n0', 'user_prompt', 'short label', 'input');
    const tree: ThoughtTree = {
      root,
      nodes: [root],
      edges: [],
      node_count: 1,
      edge_count: 0,
    };
    const { container } = render(<ThoughtTreeView tree={tree} />);
    const allText = container.textContent ?? '';
    expect(allText).toContain('USER PROMPT');
  });
});
