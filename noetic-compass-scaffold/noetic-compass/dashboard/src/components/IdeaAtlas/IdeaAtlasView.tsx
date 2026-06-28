/**
 * IdeaAtlasView — render an IdeaAtlas as an infinite zoomable graph.
 *
 * Scope of this scaffold:
 *
 *   - Parent component owns the toggle state (atlas | diagram), viewport,
 *     selection. This component receives the IdeaAtlas data + click handler
 *     and renders the atlas-side view.
 *   - Skeleton-only: no real reactflow integration yet. The placeholder
 *     renders a list of node summaries inside the InfiniteCanvas wrapper
 *     so the whole pipeline (parent → toggle → view → click → context) can
 *     be wired in advance of real rendering.
 *
 * Visual semantics (locked in for the real renderer):
 *
 *   - Positive-space nodes: full opacity, color-coded by Noetic.
 *   - Negative-space nodes (involution shadows): low opacity, dashed border.
 *   - Edge color/style by edge_kind:
 *       involution_pair         → dashed, neutral
 *       domain_descent          → solid arrow, blue
 *       domain_feedback         → dashed reverse arrow, blue
 *       drive_inversion         → dashed amber
 *       rpm_chain               → solid green, animated (entrainment)
 *       cluster_member          → dotted, teal
 *       register_co_presence    → solid pink (`+`)
 *       register_integration    → solid magenta with diamond head (`×`)
 *       recipe_prerequisite     → solid violet
 *       production_target       → arrow into Ω, violet
 *       trace                   → grey, generic compiler trace
 */

import { useMemo } from 'react';
import type { ReactElement } from 'react';

import { InfiniteCanvas } from './InfiniteCanvas';
import type {
  AtlasNodeClickEvent,
  IdeaAtlas,
  IdeaNode,
  ViewportTransform,
} from './types';

export interface IdeaAtlasViewProps {
  atlas: IdeaAtlas | null;
  /** Currently selected node id (highlighted). */
  selected_node_id: string | null;
  /**
   * Other-view (diagram) ids whose corresponding atlas counterparts should
   * be highlighted. Empty when the user hasn't clicked anything in either
   * view, or when the selection has no diagram-side counterpart.
   */
  highlight_node_ids?: readonly string[];
  /** Initial viewport when the atlas first appears. */
  initial_viewport?: ViewportTransform;
  /** Click handler — fires when the user clicks an atlas node. */
  on_node_click?: (event: AtlasNodeClickEvent) => void;
  /** Viewport change handler — used to preserve viewport across toggle. */
  on_viewport_change?: (transform: ViewportTransform) => void;
  /** Click on empty canvas — used to deselect. */
  on_pane_click?: () => void;
}

const NOETIC_COLORS: Record<string, string> = {
  '^0': '#94a3b8', // Idea — neutral grey
  '^1': '#a78bfa', // Mind — violet
  '^2': '#22d3ee', // Positive — cyan
  '^3': '#f87171', // Negative — red
  '^4': '#fbbf24', // Vibration — amber
  '^5': '#34d399', // Female — green (substrate)
  '^6': '#38bdf8', // Male — blue
  '^7': '#f472b6', // Rhythm — pink
  '^8': '#fb923c', // Above/Cause — orange
  '^9': '#c084fc', // Below/Effect — light violet
};

function color_for_node(node: IdeaNode): string {
  return NOETIC_COLORS[node.noetic] ?? '#22d3ee';
}

function NodeSummary(props: {
  node: IdeaNode;
  selected: boolean;
  highlighted: boolean;
  on_click: () => void;
}): ReactElement {
  const { node, selected, highlighted, on_click } = props;
  const color = color_for_node(node);
  return (
    <button
      type="button"
      onClick={on_click}
      data-testid={`atlas-node-${node.id}`}
      data-noetic={node.noetic}
      data-positive-space={node.is_positive_space}
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'flex-start',
        padding: 12,
        margin: 6,
        minWidth: 220,
        textAlign: 'left',
        borderRadius: 8,
        border: `2px ${node.is_positive_space ? 'solid' : 'dashed'} ${color}`,
        background: 'rgba(15, 23, 42, 0.75)',
        color: '#e2e8f0',
        opacity: node.is_positive_space ? 1 : 0.55,
        boxShadow: selected
          ? `0 0 0 2px ${color}, 0 0 12px ${color}`
          : highlighted
            ? `0 0 0 1px ${color}`
            : 'none',
        cursor: 'pointer',
        transition: 'box-shadow 120ms ease, opacity 120ms ease',
      }}
    >
      <span style={{ fontWeight: 600, fontSize: 14 }}>{node.label}</span>
      <span style={{ fontSize: 11, color: '#94a3b8' }}>
        intensity={node.intensity.toFixed(2)} •{' '}
        {node.is_positive_space ? 'lit' : 'absent (involution shadow)'}
      </span>
    </button>
  );
}

export function IdeaAtlasView(props: IdeaAtlasViewProps) {
  const {
    atlas,
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

  if (!atlas) {
    return (
      <div
        id="idea-atlas-view"
        role="tabpanel"
        aria-label="Idea Atlas (empty)"
        data-testid="idea-atlas-view-empty"
        style={{
          padding: 24,
          color: '#94a3b8',
          fontFamily: 'inherit',
        }}
      >
        No atlas yet — submit a prompt to see the Idea-substrate this
        prediction lit up.
      </div>
    );
  }

  return (
    <div
      id="idea-atlas-view"
      role="tabpanel"
      aria-label="Idea Atlas"
      data-testid="idea-atlas-view"
      data-generation-id={atlas.generation_id}
    >
      <InfiniteCanvas
        initial_viewport={initial_viewport}
        on_viewport_change={on_viewport_change}
        on_pane_click={on_pane_click}
        show_minimap
        show_controls
        show_background
      >
        <div
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            padding: 16,
          }}
        >
          {atlas.nodes.map((node) => (
            <NodeSummary
              key={node.id}
              node={node}
              selected={node.id === selected_node_id}
              highlighted={highlight_set.has(node.id)}
              on_click={() =>
                on_node_click?.({
                  source_view: 'atlas',
                  node_id: node.id,
                  generation_id: atlas.generation_id,
                })
              }
            />
          ))}
        </div>

        {/*
          Edge rendering is the responsibility of the real reactflow
          implementation — placeholder shows count for now.
        */}
        <div
          style={{
            padding: '8px 16px',
            fontFamily: 'ui-monospace, monospace',
            fontSize: 11,
            color: '#64748b',
          }}
          data-testid="atlas-edge-count"
        >
          {atlas.edges.length} edge(s) • cas={atlas.cas_expression}
        </div>
      </InfiniteCanvas>
    </div>
  );
}

export default IdeaAtlasView;
