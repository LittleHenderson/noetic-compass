import { useMemo, useRef, useState } from 'react';

import { colorFromCasExpression } from '../../lib/notation2DMap';

// ── Types ──

export interface Idea {
  id: string;
  text: string;
  cas_expression: string | null;
  cas_english?: string | null;
  created_at: string;
  compile_error?: string | null;
}

export interface Edge {
  source: string;
  target: string;
  score: number;
  breakdown?: Record<string, number>;
}

export interface GraphViewProps {
  ideas: Idea[];
  edges: Edge[];
  selectedId: string | null;
  pulseId?: string | null;
  onSelectIdea: (id: string | null) => void;
  width?: number;
  height?: number;
}

// ── Color from CAS expression ──
//
// Stage 23.A.1.1: this used to be a hand-rolled regex inside this file
// (`colorFromCas`). It has been replaced with `colorFromCasExpression`
// from the canonical adapter, which classifies the dominant primitive
// against the same 17-kind PrimitiveKind union as the Python source of
// truth in `cas-native/atlas/notation_2d_map.py`. The palette is now
// centralized in `notation2DMap.KIND_COLOR` so every CAS-aware renderer
// gets a deterministic color scheme without copy-pasting regex.

function colorFromCas(cas: string | null | undefined): string {
  return colorFromCasExpression(cas);
}

// ── Hand-rolled force simulation ──
// Why hand-rolled: recharts ships d3-array/scale/shape/etc but NOT d3-force,
// d3-selection, or d3-zoom. Adding d3-force would mean a new dependency.
// A standard 3-force simulation (charge + link + center) is ~80 lines and
// deterministic — fine for a few hundred nodes.

interface SimNode {
  id: string;
  x: number;
  y: number;
  vx: number;
  vy: number;
}

interface SimResult {
  nodes: Record<string, { x: number; y: number }>;
}

function runSimulation(
  ideas: Idea[],
  edges: Edge[],
  width: number,
  height: number,
  ticks = 220,
): SimResult {
  if (ideas.length === 0) return { nodes: {} };

  const cx = width / 2;
  const cy = height / 2;

  // Deterministic seed-style layout (golden angle spiral) so initial positions
  // are stable across renders and don't drift on every prop change.
  const golden = Math.PI * (3 - Math.sqrt(5));
  const radius0 = Math.min(width, height) * 0.3;
  const sim: SimNode[] = ideas.map((idea, i) => {
    const r = radius0 * Math.sqrt((i + 1) / ideas.length);
    const theta = i * golden;
    return {
      id: idea.id,
      x: cx + r * Math.cos(theta),
      y: cy + r * Math.sin(theta),
      vx: 0,
      vy: 0,
    };
  });

  const indexById = new Map(sim.map((n, i) => [n.id, i]));

  // Pre-resolve edge endpoints to indices; drop edges that reference missing
  // nodes (defensive: backend list and edges might briefly disagree).
  const links: { a: number; b: number; score: number }[] = [];
  for (const e of edges) {
    const a = indexById.get(e.source);
    const b = indexById.get(e.target);
    if (a === undefined || b === undefined || a === b) continue;
    links.push({ a, b, score: Math.max(0, Math.min(1, e.score)) });
  }

  // Force constants — tuned for ~5–80 nodes in ~600x500 viewport.
  const chargeStrength = -240; // repulsion
  const idealLinkDist = 90;
  const linkStrength = 0.06;
  const centerStrength = 0.012;
  const damping = 0.85;
  const maxVel = 12;

  for (let t = 0; t < ticks; t++) {
    const alpha = 1 - t / ticks; // anneal

    // Pairwise charge (O(n^2) — fine for small graphs)
    for (let i = 0; i < sim.length; i++) {
      for (let j = i + 1; j < sim.length; j++) {
        const dx = sim[j].x - sim[i].x;
        const dy = sim[j].y - sim[i].y;
        let dist2 = dx * dx + dy * dy;
        if (dist2 < 1) dist2 = 1;
        const dist = Math.sqrt(dist2);
        const force = (chargeStrength * alpha) / dist2;
        const fx = (force * dx) / dist;
        const fy = (force * dy) / dist;
        sim[i].vx -= fx;
        sim[i].vy -= fy;
        sim[j].vx += fx;
        sim[j].vy += fy;
      }
    }

    // Link spring force (stronger links pull harder)
    for (const link of links) {
      const a = sim[link.a];
      const b = sim[link.b];
      const dx = b.x - a.x;
      const dy = b.y - a.y;
      const dist = Math.sqrt(dx * dx + dy * dy) || 0.001;
      const k = linkStrength * (0.4 + link.score) * alpha;
      const delta = (dist - idealLinkDist) * k;
      const fx = (delta * dx) / dist;
      const fy = (delta * dy) / dist;
      a.vx += fx;
      a.vy += fy;
      b.vx -= fx;
      b.vy -= fy;
    }

    // Centering pull
    for (const n of sim) {
      n.vx += (cx - n.x) * centerStrength * alpha;
      n.vy += (cy - n.y) * centerStrength * alpha;
    }

    // Integrate + damp + clamp
    for (const n of sim) {
      n.vx *= damping;
      n.vy *= damping;
      if (n.vx > maxVel) n.vx = maxVel;
      if (n.vx < -maxVel) n.vx = -maxVel;
      if (n.vy > maxVel) n.vy = maxVel;
      if (n.vy < -maxVel) n.vy = -maxVel;
      n.x += n.vx;
      n.y += n.vy;
      // keep inside viewport with margin for radius
      if (n.x < 24) n.x = 24;
      if (n.x > width - 24) n.x = width - 24;
      if (n.y < 24) n.y = 24;
      if (n.y > height - 24) n.y = height - 24;
    }
  }

  const nodes: Record<string, { x: number; y: number }> = {};
  for (const n of sim) {
    nodes[n.id] = { x: n.x, y: n.y };
  }
  return { nodes };
}

function truncate(s: string, n: number): string {
  if (s.length <= n) return s;
  return s.slice(0, n - 1) + '…';
}

export function GraphView({
  ideas,
  edges,
  selectedId,
  pulseId,
  onSelectIdea,
  width = 800,
  height = 560,
}: GraphViewProps) {
  const [hoverId, setHoverId] = useState<string | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);

  // Recompute layout when the set of node ids or edge set changes — not
  // on every selection change.
  const nodeIdsKey = useMemo(
    () => ideas.map((i) => i.id).sort().join('|'),
    [ideas],
  );
  const edgesKey = useMemo(
    () =>
      edges
        .map((e) =>
          [e.source, e.target].sort().join('>') + ':' + e.score.toFixed(3),
        )
        .sort()
        .join('|'),
    [edges],
  );

  const layout = useMemo(
    () => runSimulation(ideas, edges, width, height),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [nodeIdsKey, edgesKey, width, height],
  );

  // Build a quick lookup once for tooltip rendering
  const ideaById = useMemo(() => {
    const m = new Map<string, Idea>();
    for (const i of ideas) m.set(i.id, i);
    return m;
  }, [ideas]);

  // ── Empty state ──
  if (ideas.length === 0) {
    return (
      <div
        className="flex items-center justify-center rounded-lg border border-white/[0.06] bg-white/[0.02]"
        style={{ width: '100%', maxWidth: width, height }}
      >
        <p className="text-slate-500 font-mono text-xs text-center px-6">
          No ideas yet — capture one above to start your atlas.
        </p>
      </div>
    );
  }

  const hovered = hoverId ? ideaById.get(hoverId) : null;
  const hoverPos = hoverId ? layout.nodes[hoverId] : null;

  return (
    <div
      className="relative rounded-lg border border-white/[0.06] bg-black/30"
      style={{ width: '100%', maxWidth: width, height }}
    >
      <svg
        ref={svgRef}
        width="100%"
        height="100%"
        viewBox={`0 0 ${width} ${height}`}
        className="cursor-default"
        onClick={(e) => {
          // Click on empty area (not on a node) clears selection
          if (e.target === svgRef.current) {
            onSelectIdea(null);
          }
        }}
      >
        {/* Edges first, so nodes render on top */}
        <g>
          {edges.map((e, i) => {
            const a = layout.nodes[e.source];
            const b = layout.nodes[e.target];
            if (!a || !b) return null;
            const sw = 0.5 + Math.max(0, Math.min(1, e.score)) * 2.0;
            const involvesSelected =
              selectedId !== null &&
              (e.source === selectedId || e.target === selectedId);
            return (
              <line
                key={`e${i}-${e.source}-${e.target}`}
                x1={a.x}
                y1={a.y}
                x2={b.x}
                y2={b.y}
                stroke={involvesSelected ? '#22d3ee' : '#475569'}
                strokeOpacity={involvesSelected ? 0.85 : 0.45}
                strokeWidth={sw}
              />
            );
          })}
        </g>

        {/* Nodes */}
        <g>
          {ideas.map((idea) => {
            const pos = layout.nodes[idea.id];
            if (!pos) return null;
            const fill = colorFromCas(idea.cas_expression);
            const isSelected = idea.id === selectedId;
            const isHover = idea.id === hoverId;
            return (
              <g
                key={idea.id}
                transform={`translate(${pos.x}, ${pos.y})`}
                style={{ cursor: 'pointer' }}
                role="button"
                tabIndex={0}
                aria-label={`Select idea: ${truncate(idea.text, 80)}`}
                onClick={(ev) => {
                  ev.stopPropagation();
                  onSelectIdea(idea.id);
                }}
                onKeyDown={(ev) => {
                  if (ev.key === 'Enter' || ev.key === ' ') {
                    ev.preventDefault();
                    onSelectIdea(idea.id);
                  }
                }}
                onMouseEnter={() => setHoverId(idea.id)}
                onMouseLeave={() =>
                  setHoverId((prev) => (prev === idea.id ? null : prev))
                }
              >
                <circle
                  r={18}
                  fill={fill}
                  fillOpacity={isSelected ? 0.35 : 0.2}
                  stroke={isSelected ? '#fafafa' : isHover ? fill : fill}
                  strokeOpacity={isSelected ? 1 : isHover ? 0.95 : 0.7}
                  strokeWidth={isSelected ? 2.5 : 1.5}
                />
                {idea.id === pulseId && (
                  <circle
                    key={`pulse-${pulseId}`}
                    r={21}
                    fill="none"
                    stroke={fill}
                    strokeWidth={2}
                    strokeOpacity={0.75}
                  >
                    <animate
                      attributeName="r"
                      values="21;34"
                      dur="900ms"
                      fill="freeze"
                    />
                    <animate
                      attributeName="stroke-opacity"
                      values="0.75;0"
                      dur="900ms"
                      fill="freeze"
                    />
                  </circle>
                )}
                {/* Inner dot for visual punch */}
                <circle r={4} fill={fill} fillOpacity={0.9} />
              </g>
            );
          })}
        </g>

        {/* Tooltip — rendered as foreignObject so we get text wrapping */}
        {hovered && hoverPos && (
          <g
            transform={`translate(${Math.min(
              hoverPos.x + 24,
              width - 220,
            )}, ${Math.max(hoverPos.y - 16, 8)})`}
            pointerEvents="none"
          >
            <rect
              width={210}
              height={48}
              rx={4}
              fill="#0d1117"
              fillOpacity={0.95}
              stroke="#22d3ee"
              strokeOpacity={0.4}
              strokeWidth={1}
            />
            <text
              x={8}
              y={18}
              fill="#cbd5e1"
              fontFamily="ui-monospace, monospace"
              fontSize={10}
            >
              {truncate(hovered.text, 38)}
            </text>
            <text
              x={8}
              y={36}
              fill="#22d3ee"
              fontFamily="ui-monospace, monospace"
              fontSize={10}
            >
              {hovered.cas_expression
                ? truncate(hovered.cas_expression, 38)
                : '(no CAS)'}
            </text>
          </g>
        )}
      </svg>
    </div>
  );
}

export default GraphView;
