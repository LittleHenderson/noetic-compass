/**
 * ThoughtTreeView — SVG renderer for the Atlas v0 Thought Tree.
 *
 * Consumes the JSON shape emitted by
 * `cas-native/inference/thought_tree.py::build_thought_tree`. v0 layout is
 * deterministic top-down hierarchical (root at top, subtree width allocated
 * by leaf count). No force-directed layout, no foreign deps; SVG + Tailwind 4.
 *
 * Pan + zoom via mouse drag + wheel — mirrors GraphView.tsx conventions.
 * Local ThoughtTreeNode/Edge types keep this independent from Agent B's
 * `lib/trace.ts` until integration time.
 */
import {
  type CSSProperties,
  type KeyboardEvent as ReactKeyboardEvent,
  type MouseEvent as ReactMouseEvent,
  type WheelEvent as ReactWheelEvent,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';

// ── Types — duck-typed against thought_tree.py::build_thought_tree ──────────

/** A single node in the Thought Tree, matching the Python builder's shape. */
export interface ThoughtTreeNode {
  id: string;
  node_key: string;
  kind: string;
  role: string;
  label: string;
  normalized_label?: string;
  /** Optional axis_attrs — kind-specific structured metadata for the node. */
  axis_attrs?: Record<string, unknown>;
  /** Optional long text (model output, full CAS expression, etc.). */
  text?: string;
  /** Present on the nested `root` view, absent from the flat array. */
  children?: ThoughtTreeNode[];
}

/** A single edge in the Thought Tree, matching the Python builder's shape. */
export interface ThoughtTreeEdge {
  id: string;
  edge_key: string;
  source: string;
  target: string;
  source_key: string;
  target_key: string;
  kind: string;
}

/** The full Thought Tree object — Python's `build_thought_tree` return value. */
export interface ThoughtTree {
  root: ThoughtTreeNode;
  nodes: ThoughtTreeNode[];
  edges: ThoughtTreeEdge[];
  node_count: number;
  edge_count: number;
}

export interface ThoughtTreeViewProps {
  tree: ThoughtTree;
  onNodeClick?: (node: ThoughtTreeNode) => void;
  selectedNodeId?: string | null;
  className?: string;
}

// ── Color palette per node kind — raw hex so SVG fill/stroke share values ─

interface KindPalette {
  fill: string;
  stroke: string;
  kind: string;
}

const KIND_PALETTE: Record<string, KindPalette> = {
  user_prompt: { fill: '#3b82f6', stroke: '#60a5fa', kind: 'user_prompt' },
  nl_bridge: { fill: '#8b5cf6', stroke: '#a78bfa', kind: 'nl_bridge' },
  cas_expression: { fill: '#14b8a6', stroke: '#2dd4bf', kind: 'cas_expression' },
  model_generation: { fill: '#10b981', stroke: '#34d399', kind: 'model_generation' },
  identifier_attempt: { fill: '#06b6d4', stroke: '#22d3ee', kind: 'identifier_attempt' },
  slot_pattern: { fill: '#f59e0b', stroke: '#fbbf24', kind: 'slot_pattern' },
  confidence_marker: { fill: '#f43f5e', stroke: '#fb7185', kind: 'confidence_marker' },
};

const UNKNOWN_PALETTE: KindPalette = {
  fill: '#64748b',
  stroke: '#94a3b8',
  kind: 'unknown',
};

function paletteFor(kind: string): KindPalette {
  return KIND_PALETTE[kind] ?? UNKNOWN_PALETTE;
}

// ── Truncation helper ──────────────────────────────────────────────────────

const LABEL_MAX_CHARS = 32;

function truncate(label: string, max: number = LABEL_MAX_CHARS): string {
  if (!label) return '';
  if (label.length <= max) return label;
  return `${label.slice(0, max - 1)}…`;
}

// ── Layout — hierarchical top-down, subtree width ∝ leaf count ────────────

interface NodePos {
  x: number;
  y: number;
  depth: number;
}

interface LayoutResult {
  positions: Record<string, NodePos>;
  bounds: { minX: number; maxX: number; minY: number; maxY: number };
  bfsOrder: string[];
}

const NODE_W = 160;
const NODE_H = 44;
const H_GAP = 24;
const V_GAP = 80;

function leafCount(node: ThoughtTreeNode): number {
  const children = node.children ?? [];
  if (children.length === 0) return 1;
  return children.reduce((acc, c) => acc + leafCount(c), 0);
}

function buildLayout(root: ThoughtTreeNode): LayoutResult {
  const positions: Record<string, NodePos> = {};
  const slotWidth = NODE_W + H_GAP;

  function place(node: ThoughtTreeNode, depth: number, leftSlot: number): number {
    const myLeaves = leafCount(node);
    const myWidthSlots = myLeaves;
    // Center this node above its allocated slot range.
    const centerSlot = leftSlot + myWidthSlots / 2;
    const x = centerSlot * slotWidth;
    const y = depth * V_GAP;
    positions[node.id] = { x, y, depth };

    let cursorSlot = leftSlot;
    for (const child of node.children ?? []) {
      const childLeaves = leafCount(child);
      place(child, depth + 1, cursorSlot);
      cursorSlot += childLeaves;
    }
    return myWidthSlots;
  }

  place(root, 0, 0);

  // BFS order — used to stagger the entry animation so the tree "unfolds"
  // from root → leaves rather than appearing all at once.
  const bfsOrder: string[] = [];
  const queue: ThoughtTreeNode[] = [root];
  while (queue.length > 0) {
    const node = queue.shift() as ThoughtTreeNode;
    bfsOrder.push(node.id);
    for (const c of node.children ?? []) queue.push(c);
  }

  // Bounds — used to size the viewBox. Add the node footprint so labels at
  // the edges have room.
  let minX = Infinity;
  let maxX = -Infinity;
  let minY = Infinity;
  let maxY = -Infinity;
  for (const pos of Object.values(positions)) {
    if (pos.x - NODE_W / 2 < minX) minX = pos.x - NODE_W / 2;
    if (pos.x + NODE_W / 2 > maxX) maxX = pos.x + NODE_W / 2;
    if (pos.y - NODE_H / 2 < minY) minY = pos.y - NODE_H / 2;
    if (pos.y + NODE_H / 2 > maxY) maxY = pos.y + NODE_H / 2;
  }
  if (!Number.isFinite(minX)) {
    minX = 0;
    maxX = NODE_W;
    minY = 0;
    maxY = NODE_H;
  }

  return {
    positions,
    bounds: { minX, maxX, minY, maxY },
    bfsOrder,
  };
}

// ── Edge path — smooth cubic Bezier from parent-bottom to child-top ───────

function edgePath(a: NodePos, b: NodePos): string {
  const x1 = a.x;
  const y1 = a.y + NODE_H / 2;
  const x2 = b.x;
  const y2 = b.y - NODE_H / 2;
  const dy = Math.max(20, (y2 - y1) / 2);
  return `M ${x1} ${y1} C ${x1} ${y1 + dy}, ${x2} ${y2 - dy}, ${x2} ${y2}`;
}

// ── Inject keyframe animation once per page (BFS-staggered entry) ─────────

const ENTRY_STYLE_ID = 'thought-tree-view-entry-keyframes';
const ENTRY_CSS = `
@keyframes thought-tree-node-in {
  0%   { opacity: 0; transform: scale(0.85); }
  60%  { opacity: 1; }
  100% { opacity: 1; transform: scale(1); }
}
@keyframes thought-tree-edge-in {
  0%   { opacity: 0; stroke-dashoffset: 200; }
  100% { opacity: 1; stroke-dashoffset: 0; }
}
.thought-tree-node-anim { animation: thought-tree-node-in 320ms ease-out both; transform-origin: center; transform-box: fill-box; }
.thought-tree-edge-anim { animation: thought-tree-edge-in 320ms ease-out both; stroke-dasharray: 200; }
`;

function injectEntryStyles(): void {
  if (typeof document === 'undefined') return;
  if (document.getElementById(ENTRY_STYLE_ID)) return;
  const style = document.createElement('style');
  style.id = ENTRY_STYLE_ID;
  style.textContent = ENTRY_CSS;
  document.head.appendChild(style);
}

// ── Empty-state card ───────────────────────────────────────────────────────

function EmptyState({ className }: { className?: string }) {
  return (
    <div
      data-testid="thought-tree-empty"
      className={[
        'flex h-full min-h-[280px] w-full items-center justify-center',
        'rounded-lg border border-white/[0.06] bg-white/[0.02]',
        'dark:border-white/[0.08] dark:bg-white/[0.03]',
        className ?? '',
      ]
        .filter(Boolean)
        .join(' ')}
    >
      <div className="flex flex-col items-center gap-3 px-6 py-8 text-center">
        <svg
          aria-hidden="true"
          width="36"
          height="36"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="text-slate-500 dark:text-slate-400"
        >
          <circle cx="12" cy="5" r="2" />
          <circle cx="6" cy="19" r="2" />
          <circle cx="18" cy="19" r="2" />
          <path d="M12 7v4M6 17l5-6M18 17l-5-6" />
        </svg>
        <p className="font-mono text-xs text-slate-500 dark:text-slate-400">
          Load a trace to see the Thought Tree
        </p>
      </div>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────

export function ThoughtTreeView({
  tree,
  onNodeClick,
  selectedNodeId,
  className,
}: ThoughtTreeViewProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [hoverId, setHoverId] = useState<string | null>(null);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const dragState = useRef<{ startX: number; startY: number; panX: number; panY: number } | null>(null);

  useEffect(() => {
    injectEntryStyles();
  }, []);

  const layout = useMemo(() => {
    if (!tree.root || (tree.node_count ?? 0) === 0) return null;
    return buildLayout(tree.root);
  }, [tree.root, tree.node_count]);

  // BFS index → ms delay for staggered entry animation.
  const bfsDelayMs = useMemo(() => {
    const out: Record<string, number> = {};
    if (!layout) return out;
    layout.bfsOrder.forEach((id, idx) => {
      out[id] = Math.min(idx * 40, 600);
    });
    return out;
  }, [layout]);

  // ── Pan + zoom handlers ──────────────────────────────────────────────────
  const onWheel = useCallback((e: ReactWheelEvent<SVGSVGElement>) => {
    e.preventDefault();
    const delta = -e.deltaY * 0.0015;
    setZoom((z) => Math.max(0.4, Math.min(3, z + delta)));
  }, []);

  const onMouseDown = useCallback((e: ReactMouseEvent<SVGSVGElement>) => {
    // Only start panning on background drag — not on a node click.
    const target = e.target as SVGElement;
    if (target.dataset?.role !== 'background') return;
    dragState.current = { startX: e.clientX, startY: e.clientY, panX: pan.x, panY: pan.y };
  }, [pan.x, pan.y]);

  const onMouseMove = useCallback((e: ReactMouseEvent<SVGSVGElement>) => {
    const ds = dragState.current;
    if (!ds) return;
    setPan({
      x: ds.panX + (e.clientX - ds.startX),
      y: ds.panY + (e.clientY - ds.startY),
    });
  }, []);

  const onMouseUp = useCallback(() => {
    dragState.current = null;
  }, []);

  // ── Empty-state short circuit ────────────────────────────────────────────
  if (!layout || (tree.node_count ?? 0) === 0) {
    return <EmptyState className={className} />;
  }

  const PAD = 16;
  const vbX = layout.bounds.minX - PAD;
  const vbY = layout.bounds.minY - PAD;
  const vbW = layout.bounds.maxX - layout.bounds.minX + PAD * 2;
  const vbH = layout.bounds.maxY - layout.bounds.minY + PAD * 2;

  // Compose viewBox with pan + zoom so the SVG content scrolls in user space.
  const zoomedW = vbW / zoom;
  const zoomedH = vbH / zoom;
  const zoomedX = vbX + (vbW - zoomedW) / 2 - pan.x / zoom;
  const zoomedY = vbY + (vbH - zoomedH) / 2 - pan.y / zoom;

  return (
    <div
      data-testid="thought-tree-view"
      className={[
        'relative h-full min-h-[280px] w-full',
        'rounded-lg border border-white/[0.06] bg-black/30',
        'dark:border-white/[0.08] dark:bg-black/40',
        'overflow-hidden',
        className ?? '',
      ]
        .filter(Boolean)
        .join(' ')}
    >
      <svg
        ref={svgRef}
        role="tree"
        aria-label="Thought Tree"
        width="100%"
        height="100%"
        viewBox={`${zoomedX} ${zoomedY} ${zoomedW} ${zoomedH}`}
        preserveAspectRatio="xMidYMid meet"
        onWheel={onWheel}
        onMouseDown={onMouseDown}
        onMouseMove={onMouseMove}
        onMouseUp={onMouseUp}
        onMouseLeave={onMouseUp}
        className="cursor-grab active:cursor-grabbing"
      >
        {/* Background — receives pan drag-starts */}
        <rect data-role="background" x={vbX} y={vbY} width={vbW} height={vbH} fill="transparent" />

        {/* Edges first so nodes draw on top */}
        <g>
          {tree.edges?.map((edge) => {
            const a = layout.positions[edge.source];
            const b = layout.positions[edge.target];
            if (!a || !b) return null;
            const delay = (bfsDelayMs[edge.target] ?? 0) + 120;
            const style: CSSProperties = { animationDelay: `${delay}ms` };
            const involvesSelected =
              selectedNodeId != null &&
              (edge.source === selectedNodeId || edge.target === selectedNodeId);
            return (
              <path
                key={edge.id}
                data-testid={`thought-tree-edge-${edge.id}`}
                data-edge-id={edge.id}
                d={edgePath(a, b)}
                fill="none"
                stroke={involvesSelected ? '#a78bfa' : '#475569'}
                strokeOpacity={involvesSelected ? 0.95 : 0.55}
                strokeWidth={involvesSelected ? 2 : 1.5}
                className="thought-tree-edge-anim"
                style={style}
              />
            );
          })}
        </g>

        {/* Nodes */}
        <g>
          {tree.nodes?.map((node) => {
            const pos = layout.positions[node.id];
            if (!pos) return null;
            const isSelected = node.id === selectedNodeId;
            const isHover = node.id === hoverId;
            const palette = paletteFor(node.kind);
            const delay = bfsDelayMs[node.id] ?? 0;
            const animStyle: CSSProperties = { animationDelay: `${delay}ms` };
            const labelText = truncate(node.label || node.kind);

            return (
              <g
                key={node.id}
                data-testid={`thought-tree-node-${node.id}`}
                data-node-id={node.id}
                data-kind={palette.kind}
                data-selected={isSelected ? 'true' : 'false'}
                transform={`translate(${pos.x - NODE_W / 2}, ${pos.y - NODE_H / 2})`}
                role="treeitem"
                aria-label={node.label}
                aria-selected={isSelected}
                tabIndex={0}
                className="thought-tree-node-anim cursor-pointer transition-transform duration-150 ease-out hover:scale-[1.04]"
                style={animStyle}
                onClick={(e) => {
                  e.stopPropagation();
                  onNodeClick?.(node);
                }}
                onKeyDown={(e: ReactKeyboardEvent<SVGGElement>) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    onNodeClick?.(node);
                  }
                }}
                onMouseEnter={() => setHoverId(node.id)}
                onMouseLeave={() => setHoverId((id) => (id === node.id ? null : id))}
              >
                {/* Cheap pseudo-shadow on hover/selected */}
                {(isHover || isSelected) && (
                  <rect x={2} y={4} width={NODE_W} height={NODE_H} rx={8} ry={8} fill="black" fillOpacity={0.35} />
                )}
                <rect
                  x={0} y={0} width={NODE_W} height={NODE_H} rx={8} ry={8}
                  fill={palette.fill}
                  fillOpacity={isSelected ? 0.85 : isHover ? 0.55 : 0.32}
                  stroke={isSelected ? '#fafafa' : palette.stroke}
                  strokeOpacity={isSelected ? 1 : isHover ? 0.95 : 0.7}
                  strokeWidth={isSelected ? 2 : 1.25}
                />
                {/* Kind ribbon on the left edge */}
                <rect x={0} y={0} width={4} height={NODE_H} rx={2} ry={2} fill={palette.stroke} fillOpacity={0.95} />
                <text
                  x={NODE_W / 2} y={NODE_H / 2 + 4} textAnchor="middle"
                  fontFamily="ui-sans-serif, system-ui, sans-serif"
                  fontSize={12} fontWeight={isSelected ? 600 : 500}
                  fill={isSelected ? '#0f172a' : '#e2e8f0'}
                  className="select-none"
                >
                  {labelText}
                </text>
                {/* Hover tooltip — full label is always available via SVG <title> */}
                <title>{node.label}</title>
              </g>
            );
          })}
        </g>
      </svg>

      {/* Legend — color encoding key, bottom-left overlay */}
      <div
        data-testid="thought-tree-legend"
        className="pointer-events-none absolute bottom-2 left-2 flex flex-col gap-1 rounded-md bg-black/40 px-2 py-1.5 font-mono text-[10px] text-slate-200 backdrop-blur-sm dark:bg-black/50"
        aria-hidden="true"
      >
        {Object.entries(KIND_PALETTE).map(([kind, p]) => (
          <div key={kind} className="flex items-center gap-1.5">
            <span
              className="inline-block h-2 w-2 rounded-sm"
              style={{ backgroundColor: p.stroke }}
            />
            <span>{kind}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default ThoughtTreeView;
