import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import {
  NeuralActivityMap,
  regionForHeadCommit,
} from './NeuralActivityMap';
import type { SggsHeadCommit } from '../../lib/sggs_stream';
import type {
  AtlasTraceThoughtTree,
  ThoughtTreeNode,
  ThoughtTreeRootNode,
} from '../../lib/trace';

function rootNode(
  id: string,
  kind: string,
  label: string,
  children: ThoughtTreeRootNode[] = [],
): ThoughtTreeRootNode {
  return {
    id,
    node_key: `${kind}|${label}`,
    kind,
    role: kind === 'user_prompt' ? 'input' : 'output',
    label,
    normalized_label: label.toLowerCase(),
    children,
  };
}

function sampleTree(): AtlasTraceThoughtTree {
  const child = rootNode('n1', 'model_generation', 'Model Output');
  const root = rootNode('n0', 'user_prompt', 'thought becoming action', [child]);
  const nodes: ThoughtTreeNode[] = [root, child].map((node) => ({
    id: node.id!,
    node_key: node.node_key!,
    kind: node.kind,
    role: node.role,
    label: node.label,
    normalized_label: node.normalized_label,
  }));
  return {
    root,
    nodes,
    edges: [
      {
        id: 'e0',
        edge_key: 'n0->n1',
        source: 'n0',
        target: 'n1',
        source_key: 'n0',
        target_key: 'n1',
        kind: 'parent_child',
      },
    ],
    node_count: nodes.length,
    edge_count: 1,
  };
}

function headCommit(overrides: Partial<SggsHeadCommit> = {}): SggsHeadCommit {
  return {
    kind: 'head_commit',
    turn_id: 'turn-1',
    head_index: 3,
    head_name: 'domain_descent_attention',
    node_id: 'n1',
    node_kind: 'domain_commitment',
    node_label: 'Domain Decision',
    parent_node_id: 'n0',
    axis_attrs: {
      domain: 'Operational',
      activation_layers: [{ name: 'decoder.3', l2Norm: 4.2 }],
    },
    schema_version: 'sggs_stream_v0',
    ...overrides,
  };
}

describe('NeuralActivityMap', () => {
  it('renders a derived trace map before live commits arrive', () => {
    render(<NeuralActivityMap tree={sampleTree()} commits={[]} />);

    expect(screen.getByTestId('neural-activity-map')).toBeInTheDocument();
    expect(screen.getByText('CAS Neural Activity Map')).toBeInTheDocument();
    expect(screen.getAllByText('DERIVED TRACE').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Input Field').length).toBeGreaterThan(0);
    expect(screen.getAllByText('CAS Decoder').length).toBeGreaterThan(0);
  });

  it('labels real stream mode when runtime is ready and head commits exist', () => {
    render(
      <NeuralActivityMap
        tree={sampleTree()}
        commits={[headCommit()]}
        runtimeReady
      />,
    );

    expect(screen.getAllByText('REAL MODE 7 STREAM').length).toBeGreaterThan(0);
    expect(screen.getByLabelText('Select Domain Decision')).toBeInTheDocument();
  });

  it('selects nodes from pulse markers', () => {
    const onSelectNode = vi.fn();
    render(
      <NeuralActivityMap
        tree={sampleTree()}
        commits={[headCommit()]}
        runtimeReady
        onSelectNode={onSelectNode}
      />,
    );

    fireEvent.click(screen.getByLabelText('Select Domain Decision'));

    expect(onSelectNode).toHaveBeenCalledWith('n1');
  });

  it('maps copy and pointer commits to the copy region', () => {
    expect(
      regionForHeadCommit(
        headCommit({
          head_name: 'copy_pointer_head',
          node_kind: 'identifier_attempt',
          node_label: 'stageA0_4_857',
          axis_attrs: { copy_source_index: 12 },
        }),
      ),
    ).toBe('copy');
  });
});
