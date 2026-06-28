/**
 * InfiniteCanvas — zoomable / pannable scene wrapper for the IdeaAtlas + Diagram views.
 *
 * Library choice: **react-flow** (https://reactflow.dev). Rationale below.
 *
 *   - Both views render *graphs* (atlas: Idea nodes + relationship edges;
 *     diagram: compiler-derived typed graph). react-flow is purpose-built for
 *     graph rendering, with first-class support for: pan/zoom, custom node
 *     types, custom edge types, viewport state, fit-to-bounds, click handlers,
 *     and SSR-safe.
 *   - The alternative (`react-zoom-pan-pinch`) handles pan/zoom but forces
 *     the consumer to roll its own node hit-testing, edge layout, and
 *     viewport-clipping. We'd rebuild half of react-flow's primitives.
 *   - react-flow already ships a Background, MiniMap, and Controls component,
 *     all of which the user's spec calls for ("infinite zoomable space,
 *     clickable, expandable").
 *   - There is precedent in the dashboard's existing `idea-atlas/GraphView.tsx`
 *     for hand-rolled D3-style force layouts; the IdeaAtlas/ scaffold goes
 *     in the opposite direction (declarative graph-as-data) so the two
 *     approaches don't fight. Migration plan: once IdeaAtlas/ is stable,
 *     evaluate whether the older idea-atlas/GraphView.tsx should be folded in.
 *
 * Install before wiring real rendering:
 *     npm install reactflow
 *     npm install --save-dev @types/reactflow  // (types ship with the package)
 *
 * This file is a SCAFFOLD: it defines the props and exports a placeholder
 * component that the real renderer will replace. The component compiles
 * against React 19 + TypeScript without reactflow installed.
 */

import { useCallback } from 'react';
import type { ReactNode } from 'react';

import type { ViewportTransform } from './types';

export interface InfiniteCanvasProps {
  /** Initial viewport transform. Subsequent transforms are managed internally. */
  initial_viewport?: ViewportTransform;
  /** Optional fixed dimensions; otherwise the canvas fills its parent. */
  width?: number;
  height?: number;
  /** Whether to render the react-flow MiniMap. */
  show_minimap?: boolean;
  /** Whether to render the react-flow Controls (zoom in/out/fit). */
  show_controls?: boolean;
  /** Whether to render a dotted background grid. */
  show_background?: boolean;
  /** Class applied to the outer wrapper. */
  className?: string;
  /** Children — typically the rendered nodes + edges of the active view. */
  children?: ReactNode;
  /** Called when the viewport transform changes (debounced by react-flow). */
  on_viewport_change?: (transform: ViewportTransform) => void;
  /** Called when the user clicks the empty canvas (for deselection). */
  on_pane_click?: () => void;
}

/**
 * Placeholder component — does NOT render real nodes/edges yet. The
 * downstream IdeaAtlasView and DiagramView components are responsible
 * for converting their data model into reactflow's `nodes` / `edges`
 * arrays and passing them in via children-as-render-props (final
 * implementation will swap to react-flow's <ReactFlow> directly).
 */
export function InfiniteCanvas(props: InfiniteCanvasProps) {
  const {
    width,
    height,
    show_minimap = true,
    show_controls = true,
    show_background = true,
    className,
    children,
    on_viewport_change,
    on_pane_click,
  } = props;

  // Stable callback wrappers — prevent re-render cascades when consumers
  // pass inline arrow functions.
  const handle_pane_click = useCallback(() => {
    on_pane_click?.();
  }, [on_pane_click]);

  // NOTE: real implementation will lift these out into <ReactFlowProvider>.
  void show_minimap;
  void show_controls;
  void show_background;
  void on_viewport_change;

  return (
    <div
      className={className ?? 'idea-atlas-canvas'}
      style={{
        width: width ?? '100%',
        height: height ?? '100%',
        position: 'relative',
        overflow: 'hidden',
      }}
      onClick={handle_pane_click}
      data-testid="infinite-canvas-scaffold"
    >
      {/* Real implementation:
          <ReactFlow
            nodes={nodes}
            edges={edges}
            defaultViewport={initial_viewport}
            onMove={(_, viewport) => on_viewport_change?.(viewport)}
            onPaneClick={handle_pane_click}
            fitView
            minZoom={0.1}
            maxZoom={4}
          >
            {show_background && <Background />}
            {show_controls && <Controls />}
            {show_minimap && <MiniMap />}
          </ReactFlow>
      */}
      {children}
    </div>
  );
}

export default InfiniteCanvas;
