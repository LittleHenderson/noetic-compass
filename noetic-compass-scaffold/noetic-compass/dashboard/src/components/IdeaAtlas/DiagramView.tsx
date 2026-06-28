/**
 * DiagramView — render the compiler's typed CAS diagram.
 *
 * The diagram is the *other half* of the atlas/diagram toggle. Unlike the
 * Idea Atlas (which surfaces ^0/^5 substrate Ideas), the diagram is the
 * compiler-derived typed graph:
 *
 *   - state nodes (with typed Noetic / Domain / Drive / Register attributes)
 *   - cluster containers (NoeticCluster, StateSet, RelationCluster, etc.)
 *   - relation arrows (membership ∈, subset ⊆, product ×, recipe →)
 *   - layout-hint metadata (radial / dependency / recipe / containment / topos)
 *
 * Source of truth for the diagram's wire shape:
 *   `api/notation/compiler.py` (build_diagram, ≈ line 5045)
 *   `api/routes/notation.py` (response includes a `diagram` field)
 *
 * This scaffold renders a placeholder list. The real renderer reuses
 * `InfiniteCanvas` (= reactflow) so atlas + diagram share viewport
 * conventions, zoom controls, and pan behaviour. Selection state and
 * generation_id live in the parent (an IdeaAtlasContext provider).
 */

import { useMemo } from 'react';
import type { ReactElement } from 'react';

import { InfiniteCanvas } from './InfiniteCanvas';
import type {
  AtlasNodeClickEvent,
  CasDiagram,
  DiagramNode,
  ViewportTransform,
} from './types';

export interface DiagramViewProps {
  diagram: CasDiagram | null;
  generation_id: string | null;
  selected_node_id: string | null;
  /** Atlas-side ids whose diagram counterparts should be highlighted. */
  highlight_node_ids?: readonly string[];
  initial_viewport?: ViewportTransform;
  on_node_click?: (event: AtlasNodeClickEvent) => void;
  on_viewport_change?: (transform: ViewportTransform) => void;
  on_pane_click?: () => void;
}

const DIAGRAM_KIND_COLORS: Record<string, string> = {
  state: '#22d3ee',
  cluster: '#14b8a6',
  omega: '#a78bfa',
  recipe: '#f472b6',
  rpm_chain: '#34d399',
  inversion: '#f87171',
  relation: '#fbbf24',
};

function color_for_diagram_node(node: DiagramNode): string {
  if (node.kind && DIAGRAM_KIND_COLORS[node.kind]) {
    return DIAGRAM_KIND_COLORS[node.kind];
  }
  if (node.noetic) {
    // Same Noetic palette as IdeaAtlasView so a node's color matches
    // across the toggle.
    return '#22d3ee';
  }
  return '#64748b';
}

function DiagramNodeSummary(props: {
  node: DiagramNode;
  selected: boolean;
  highlighted: boolean;
  on_click: () => void;
}): ReactElement {
  const { node, selected, highlighted, on_click } = props;
  const color = color_for_diagram_node(node);
  return (
    <button
      type="button"
      onClick={on_click}
      data-testid={`diagram-node-${node.id}`}
      data-kind={node.kind ?? 'unknown'}
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'flex-start',
        padding: 12,
        margin: 6,
        minWidth: 220,
        textAlign: 'left',
        borderRadius: 8,
        border: `2px solid ${color}`,
        background: 'rgba(15, 23, 42, 0.75)',
        color: '#e2e8f0',
        boxShadow: selected
          ? `0 0 0 2px ${color}, 0 0 12px ${color}`
          : highlighted
            ? `0 0 0 1px ${color}`
            : 'none',
        cursor: 'pointer',
        transition: 'box-shadow 120ms ease',
      }}
    >
      <span style={{ fontWeight: 600, fontSize: 14 }}>{node.label}</span>
      <span style={{ fontSize: 11, color: '#94a3b8' }}>
        kind={node.kind ?? 'unknown'}
        {node.noetic ? ` • ${node.noetic}` : ''}
        {node.domain ? `^${node.domain}` : ''}
        {node.drive ? `_{${node.drive}}` : ''}
        {node.register ? `|${node.register}` : ''}
      </span>
    </button>
  );
}

export function DiagramView(props: DiagramViewProps) {
  const {
    diagram,
    generation_id,
    selected_node_id,
    highlight_node_ids = [],
    initial_viewport,
    on_node_click,
    on_viewport_change,
    on_pane_click,
  } = props;

  const highlight_set = useMemo(
    () => new Set(highlight_node_ids),
    [highlight_node_ids],
  );

  if (!diagram) {
    return (
      <div
        id="diagram-view"
        role="tabpanel"
        aria-label="Notation Diagram (empty)"
        data-testid="diagram-view-empty"
        style={{ padding: 24, color: '#94a3b8' }}
      >
        No diagram yet — the compiler hasn't produced a typed graph for this
        prediction.
      </div>
    );
  }

  return (
    <div
      id="diagram-view"
      role="tabpanel"
      aria-label="Notation Diagram"
      data-testid="diagram-view"
      data-generation-id={diagram.generation_id ?? generation_id ?? ''}
    >
      <InfiniteCanvas
        initial_viewport={initial_viewport}
        on_viewport_change={on_viewport_change}
        on_pane_click={on_pane_click}
        show_minimap
        show_controls
        show_background
      >
        <div style={{ display: 'flex', flexWrap: 'wrap', padding: 16 }}>
          {diagram.nodes.map((node) => (
            <DiagramNodeSummary
              key={node.id}
              node={node}
              selected={node.id === selected_node_id}
              highlighted={highlight_set.has(node.id)}
              on_click={() => {
                if (!generation_id && !diagram.generation_id) return;
                on_node_click?.({
                  source_view: 'diagram',
                  node_id: node.id,
                  generation_id:
                    diagram.generation_id ?? generation_id ?? '',
                });
              }}
            />
          ))}
        </div>

        <div
          style={{
            padding: '8px 16px',
            fontFamily: 'ui-monospace, monospace',
            fontSize: 11,
            color: '#64748b',
          }}
          data-testid="diagram-edge-count"
        >
          {diagram.edges.length} edge(s) • {diagram.containers.length}{' '}
          container(s) • layout={diagram.layout_hint ?? 'auto'}
        </div>
      </InfiniteCanvas>
    </div>
  );
}

export default DiagramView;
