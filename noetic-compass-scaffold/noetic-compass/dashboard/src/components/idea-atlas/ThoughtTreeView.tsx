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

// Human-readable chip labels for the kind badge on each card. The
// underlying `kind` field stays snake_case for stable selectors and
// machine consumers; the chip surfaces a polished label.
const KIND_DISPLAY: Record<string, string> = {
  user_prompt: 'USER PROMPT',
  nl_bridge: 'NL BRIDGE',
  cas_expression: 'CAS',
  model_generation: 'MODEL OUTPUT',
  identifier_attempt: 'IDENTIFIER',
  slot_pattern: 'SLOT TRACE',
  confidence_marker: 'CONFIDENCE',
};

function kindLabel(kind: string): string {
  return KIND_DISPLAY[kind] ?? kind.replace(/_/g, ' ').toUpperCase();
}

function paletteFor(kind: string): KindPalette {
  return KIND_PALETTE[kind] ?? UNKNOWN_PALETTE;
}

// ── Truncation + wrap helpers ─────────────────────────────────────────────

const LABEL_LINE_CHARS = 30;
const LABEL_MAX_LINES = 2;

/**
 * Wrap a single-line label into up to `maxLines` lines of at most
 * `lineMax` characters each, breaking on whitespace where possible.
 * Hard-cuts words that are themselves longer than `lineMax`. When the
 * label overflows the line budget, the final line is ellipsized with
 * `…` so the visible text always signals truncation.
 *
 * Used inside SVG <text> via <tspan> so the card looks like a real
 * thought card instead of a single truncated label.
 */
function wrapLabel(
  label: string,
  lineMax: number = LABEL_LINE_CHARS,
  maxLines: number = LABEL_MAX_LINES,
): string[] {
  const normalized = (label || '').replace(/\s+/g, ' ').trim();
  if (!normalized) return [''];
  const remaining: string[] = normalized.split(' ');
  const lines: string[] = [];
  let current = '';
  while (remaining.length > 0 && lines.length < maxLines) {
    const w = remaining[0];
    // Hard-split words longer than the line budget.
    if (w.length > lineMax) {
      if (current) {
        lines.push(current);
        current = '';
        if (lines.length >= maxLines) break;
      }
      lines.push(w.slice(0, lineMax));
      remaining[0] = w.slice(lineMax);
      continue;
    }
    const candidate = current ? `${current} ${w}` : w;
    if (candidate.length <= lineMax) {
      current = candidate;
      remaining.shift();
    } else {
      // candidate too long — flush the current line and retry this
      // word on the next line.
      lines.push(current);
      current = '';
    }
  }
  if (current && lines.length < maxLines) lines.push(current);
  // If content remains (words left OR an unflushed `current` that
  // wouldn't fit), ellipsize the final visible line.
  const overflowed = remaining.length > 0 || (current && lines.length >= maxLines);
  if (overflowed && lines.length > 0) {
    const last = lines[lines.length - 1];
    if (!last.endsWith('…')) {
      const cap = Math.max(1, lineMax - 1);
      lines[lines.length - 1] = last.length >= cap
        ? `${last.slice(0, cap)}…`
        : `${last}…`;
    }
  }
  return lines;
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

// Card geometry — picked so the demo trace (6 nodes / 5 edges) fills a
// stakeholder-grade ~720×580 viewport without feeling cramped or tiny.
// These are visual choices, not load-bearing; future prop control
// noted in Agent C's report. (Codex audit 2026-05-13: bigger, more
// readable cards — "thought cards, not tiny labels.")
const NODE_W = 240;
const NODE_H = 96;
const H_GAP = 48;
const V_GAP = 168;
const NODE_PADDING = 14;

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
  const containerRef = useRef<HTMLDivElement>(null);
  const [hoverId, setHoverId] = useState<string | null>(null);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [isFullscreen, setIsFullscreen] = useState(false);

  useEffect(() => {
    const onChange = () => {
      setIsFullscreen(document.fullscreenElement === containerRef.current);
    };
    document.addEventListener('fullscreenchange', onChange);
    return () => document.removeEventListener('fullscreenchange', onChange);
  }, []);

  const toggleFullscreen = useCallback(() => {
    const el = containerRef.current;
    if (!el) return;
    if (document.fullscreenElement === el) {
      void document.exitFullscreen?.();
    } else {
      void el.requestFullscreen?.();
    }
  }, []);
  const dragState = useRef<{ startX: number; startY: number; panX: number; panY: number } | null>(null);

  useEffect(() => {
    injectEntryStyles();
  }, []);

  const layout = useMemo(() => {
    if (!tree.root || (tree.node_count ?? 0) === 0) return null;
    return buildLayout(tree.root);
  }, [tree.root, tree.node_count]);

  // BFS index → ms delay for staggered entry animation. Slowed slightly
  // so the tree "unfolds" visibly rather than blinking in.
  const bfsDelayMs = useMemo(() => {
    const out: Record<string, number> = {};
    if (!layout) return out;
    layout.bfsOrder.forEach((id, idx) => {
      out[id] = Math.min(idx * 75, 900);
    });
    return out;
  }, [layout]);

  // Flat lookup: node id → kind. Used by the edge renderer to color
  // each edge by its target node's palette.
  const nodeKindById = useMemo(() => {
    const out: Record<string, string> = {};
    for (const n of tree.nodes ?? []) out[n.id] = n.kind;
    return out;
  }, [tree.nodes]);

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
      ref={containerRef}
      data-testid="thought-tree-view"
      data-fullscreen={isFullscreen ? 'true' : 'false'}
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

        {/* Edges first so nodes draw on top. Per-edge color is the
            target node's kind palette so the eye reads "this thought
            flowed INTO that node." Dim base was hard to see in the
            stakeholder demo (user feedback 2026-05-13) — bumped to
            0.85 opacity 2px stroke. */}
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
            const targetKind = nodeKindById[edge.target] ?? 'unknown';
            const targetPalette = paletteFor(targetKind);
            const stroke = involvesSelected ? '#fafafa' : targetPalette.stroke;
            const strokeOpacity = involvesSelected ? 1 : 0.85;
            const strokeWidth = involvesSelected ? 3 : 2;
            return (
              <g key={edge.id}>
                <path
                  data-testid={`thought-tree-edge-${edge.id}`}
                  data-edge-id={edge.id}
                  d={edgePath(a, b)}
                  fill="none"
                  stroke={stroke}
                  strokeOpacity={strokeOpacity}
                  strokeWidth={strokeWidth}
                  strokeLinecap="round"
                  className="thought-tree-edge-anim"
                  style={style}
                />
                {/* Arrowhead — filled dot at the target end so direction
                    is obvious. Matches target node's stroke color. */}
                <circle
                  cx={b.x}
                  cy={b.y - NODE_H / 2 - 2}
                  r={involvesSelected ? 5 : 4}
                  fill={stroke}
                  fillOpacity={strokeOpacity}
                  className="thought-tree-edge-anim"
                  style={style}
                />
              </g>
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
            // Two-line wrapped label so cards read as real thought cards,
            // not single-line truncated chips.
            const labelLines = wrapLabel(node.label || kindLabel(node.kind));
            const chipLabel = kindLabel(node.kind);
            // Card geometry — solid dark background + colored ribbon +
            // a kind chip above the wrapped title. The previous card was
            // a small translucent rectangle with one truncated label;
            // this version reads as a stakeholder-grade thought card.
            const cardFill = '#0b1220';
            const cardFillOpacity = isSelected ? 0.98 : isHover ? 0.94 : 0.88;
            const cardStrokeOpacity = isSelected ? 1 : isHover ? 0.95 : 0.75;
            const cardStroke = isSelected ? '#fafafa' : palette.stroke;
            const chipWidth = Math.min(NODE_W - NODE_PADDING * 2, 8 + chipLabel.length * 6.4);

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
                className="thought-tree-node-anim cursor-pointer transition-transform duration-150 ease-out hover:scale-[1.03]"
                style={animStyle}
                pointerEvents="all"
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
                {/* Invisible click-target rect that covers the full card
                    footprint. Guarantees the click hits the <g> handler
                    even when the pointer lands on whitespace inside the
                    card (between chip and title etc.). */}
                <rect
                  x={0}
                  y={0}
                  width={NODE_W}
                  height={NODE_H}
                  rx={12}
                  ry={12}
                  fill="transparent"
                  pointerEvents="all"
                />
                {/* Drop shadow — always-on subtle, brighter on hover/selected */}
                <rect
                  x={3}
                  y={6}
                  width={NODE_W}
                  height={NODE_H}
                  rx={12}
                  ry={12}
                  fill="black"
                  fillOpacity={isSelected ? 0.5 : isHover ? 0.42 : 0.25}
                />
                {/* Card body — solid dark fill so text is always readable */}
                <rect
                  x={0}
                  y={0}
                  width={NODE_W}
                  height={NODE_H}
                  rx={12}
                  ry={12}
                  fill={cardFill}
                  fillOpacity={cardFillOpacity}
                  stroke={cardStroke}
                  strokeOpacity={cardStrokeOpacity}
                  strokeWidth={isSelected ? 3 : 1.5}
                />
                {/* Selected glow — a second outer stroke pulse so the
                    user sees their click registered without needing
                    to look at the side panel. */}
                {isSelected && (
                  <rect
                    x={-3}
                    y={-3}
                    width={NODE_W + 6}
                    height={NODE_H + 6}
                    rx={14}
                    ry={14}
                    fill="none"
                    stroke={palette.stroke}
                    strokeOpacity={0.95}
                    strokeWidth={2}
                    pointerEvents="none"
                  />
                )}
                {/* Kind-colored ribbon on the left edge */}
                <rect
                  x={0}
                  y={0}
                  width={6}
                  height={NODE_H}
                  rx={3}
                  ry={3}
                  fill={palette.stroke}
                  fillOpacity={0.98}
                />
                {/* Kind chip — palette-tinted pill */}
                <g
                  transform={`translate(${NODE_PADDING}, ${NODE_PADDING - 2})`}
                  className="select-none"
                >
                  <rect
                    x={0}
                    y={0}
                    width={chipWidth}
                    height={18}
                    rx={9}
                    ry={9}
                    fill={palette.fill}
                    fillOpacity={0.32}
                    stroke={palette.stroke}
                    strokeOpacity={0.7}
                    strokeWidth={1}
                  />
                  <text
                    x={chipWidth / 2}
                    y={12}
                    textAnchor="middle"
                    fontFamily="ui-monospace, SFMono-Regular, monospace"
                    fontSize={10}
                    fontWeight={700}
                    letterSpacing={0.6}
                    fill={palette.stroke}
                  >
                    {chipLabel}
                  </text>
                </g>
                {/* Wrapped title — up to 2 lines, centered horizontally */}
                <text
                  x={NODE_PADDING}
                  y={NODE_PADDING + 32}
                  fontFamily="ui-sans-serif, system-ui, sans-serif"
                  fontSize={14}
                  fontWeight={isSelected ? 700 : 600}
                  fill="#f1f5f9"
                  className="select-none"
                >
                  {labelLines.map((line, i) => (
                    <tspan
                      key={i}
                      x={NODE_PADDING}
                      dy={i === 0 ? 0 : 18}
                    >
                      {line}
                    </tspan>
                  ))}
                </text>
                {/* Hover tooltip — full label always available via SVG <title> */}
                <title>{node.label}</title>
              </g>
            );
          })}
        </g>
      </svg>

      {/* Zoom toolbar — top-right overlay. Visible controls because
          trackpad-scroll-to-zoom is not discoverable. */}
      <div
        data-testid="thought-tree-toolbar"
        className="absolute right-2 top-2 flex flex-col gap-1 rounded-md bg-black/45 p-1 backdrop-blur-sm"
      >
        <button
          type="button"
          aria-label="Zoom in"
          title="Zoom in"
          onClick={() => setZoom((z) => Math.min(3, z * 1.2))}
          className="flex h-7 w-7 items-center justify-center rounded text-slate-200 hover:bg-white/10 hover:text-white"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
        </button>
        <button
          type="button"
          aria-label="Zoom out"
          title="Zoom out"
          onClick={() => setZoom((z) => Math.max(0.4, z / 1.2))}
          className="flex h-7 w-7 items-center justify-center rounded text-slate-200 hover:bg-white/10 hover:text-white"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
        </button>
        <button
          type="button"
          aria-label="Reset view"
          title="Reset view (fit to screen)"
          onClick={() => {
            setZoom(1);
            setPan({ x: 0, y: 0 });
          }}
          className="flex h-7 w-7 items-center justify-center rounded text-slate-200 hover:bg-white/10 hover:text-white"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M3 9V5a2 2 0 0 1 2-2h4" />
            <path d="M21 9V5a2 2 0 0 0-2-2h-4" />
            <path d="M3 15v4a2 2 0 0 0 2 2h4" />
            <path d="M21 15v4a2 2 0 0 1-2 2h-4" />
          </svg>
        </button>
        <button
          type="button"
          aria-label={isFullscreen ? 'Exit fullscreen' : 'Enter fullscreen'}
          title={isFullscreen ? 'Exit fullscreen' : 'Fullscreen the tree'}
          onClick={toggleFullscreen}
          className="flex h-7 w-7 items-center justify-center rounded text-slate-200 hover:bg-white/10 hover:text-white"
        >
          {isFullscreen ? (
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M8 3v3a2 2 0 0 1-2 2H3" />
              <path d="M21 8h-3a2 2 0 0 1-2-2V3" />
              <path d="M3 16h3a2 2 0 0 1 2 2v3" />
              <path d="M16 21v-3a2 2 0 0 1 2-2h3" />
            </svg>
          ) : (
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M3 7V5a2 2 0 0 1 2-2h2" />
              <path d="M17 3h2a2 2 0 0 1 2 2v2" />
              <path d="M21 17v2a2 2 0 0 1-2 2h-2" />
              <path d="M7 21H5a2 2 0 0 1-2-2v-2" />
            </svg>
          )}
        </button>
        <div
          aria-hidden="true"
          className="px-0.5 pt-0.5 text-center font-mono text-[9px] text-slate-400"
        >
          {Math.round(zoom * 100)}%
        </div>
      </div>

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
            <span>{kindLabel(kind).toLowerCase()}</span>
          </div>
        ))}
      </div>

      {/* Bottom-right hint — discoverability for trackpad zoom + drag pan */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute bottom-2 right-2 rounded-md bg-black/40 px-2 py-1 font-mono text-[9px] text-slate-400 backdrop-blur-sm"
      >
        scroll to zoom · drag to pan · click a card
      </div>
    </div>
  );
}

export default ThoughtTreeView;
