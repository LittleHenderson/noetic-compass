import { useMemo, type KeyboardEvent } from 'react';
import type { SggsCommit, SggsHeadCommit } from '../../lib/sggs_stream';
import type { AtlasTraceThoughtTree, ThoughtTreeNode } from '../../lib/trace';

type EvidenceMode = 'real_activation' | 'fallback_stream' | 'derived_trace' | 'stub_demo';

type RegionKey =
  | 'input'
  | 'noetic'
  | 'domain'
  | 'foundation'
  | 'register'
  | 'copy'
  | 'decoder'
  | 'output';

interface RegionDef {
  key: RegionKey;
  label: string;
  plain: string;
  cx: number;
  cy: number;
  rx: number;
  ry: number;
  color: string;
}

interface RegionState extends RegionDef {
  score: number;
  count: number;
  selected: boolean;
}

interface ActivityMarker {
  id: string;
  nodeId: string;
  label: string;
  detail: string;
  region: RegionKey;
  x: number;
  y: number;
  color: string;
  selected: boolean;
}

export interface NeuralActivityMapProps {
  tree: AtlasTraceThoughtTree;
  commits: readonly SggsCommit[];
  selectedNodeId?: string | null;
  runtimeReady?: boolean;
  onSelectNode?: (nodeId: string) => void;
  className?: string;
}

const REGIONS: readonly RegionDef[] = [
  {
    key: 'input',
    label: 'Input Field',
    plain: 'The prompt enters the model.',
    cx: 128,
    cy: 270,
    rx: 74,
    ry: 50,
    color: '#60a5fa',
  },
  {
    key: 'noetic',
    label: 'Noetic Resolver',
    plain: 'The model starts reading the idea-shape.',
    cx: 250,
    cy: 172,
    rx: 86,
    ry: 58,
    color: '#a78bfa',
  },
  {
    key: 'domain',
    label: 'Domain Descent',
    plain: 'The model decides which context the thought belongs to.',
    cx: 396,
    cy: 130,
    rx: 94,
    ry: 62,
    color: '#2dd4bf',
  },
  {
    key: 'foundation',
    label: 'Foundation Gate',
    plain: 'Drive and foundation signals attach to the thought.',
    cx: 538,
    cy: 182,
    rx: 90,
    ry: 60,
    color: '#fbbf24',
  },
  {
    key: 'register',
    label: 'Register Gate',
    plain: 'Tone, stance, and register settle into place.',
    cx: 672,
    cy: 150,
    rx: 82,
    ry: 54,
    color: '#fb7185',
  },
  {
    key: 'copy',
    label: 'Copy Pointer',
    plain: 'Source references and identifiers are carried forward.',
    cx: 300,
    cy: 350,
    rx: 92,
    ry: 58,
    color: '#22d3ee',
  },
  {
    key: 'decoder',
    label: 'CAS Decoder',
    plain: 'The model turns structure into emitted CAS or English.',
    cx: 510,
    cy: 370,
    rx: 98,
    ry: 62,
    color: '#34d399',
  },
  {
    key: 'output',
    label: 'Output Stream',
    plain: 'The final visible answer leaves the model.',
    cx: 770,
    cy: 288,
    rx: 82,
    ry: 54,
    color: '#38bdf8',
  },
] as const;

const REGION_BY_KEY = new Map(REGIONS.map((region) => [region.key, region]));

const PIPELINE: ReadonlyArray<[RegionKey, RegionKey]> = [
  ['input', 'noetic'],
  ['noetic', 'domain'],
  ['domain', 'foundation'],
  ['foundation', 'register'],
  ['register', 'decoder'],
  ['input', 'copy'],
  ['copy', 'decoder'],
  ['decoder', 'output'],
] as const;

function isHeadCommit(commit: SggsCommit): commit is SggsHeadCommit {
  return commit.kind === 'head_commit';
}

function textHaystack(...parts: unknown[]): string {
  return parts
    .map((part) => {
      if (typeof part === 'string') return part;
      if (part && typeof part === 'object') {
        try {
          return JSON.stringify(part);
        } catch {
          return '';
        }
      }
      return String(part ?? '');
    })
    .join(' ')
    .toLowerCase();
}

export function regionForHeadCommit(commit: SggsHeadCommit): RegionKey {
  const haystack = textHaystack(
    commit.head_name,
    commit.node_kind,
    commit.node_label,
    commit.axis_attrs,
  );
  if (haystack.includes('copy') || haystack.includes('pointer') || haystack.includes('source')) {
    return 'copy';
  }
  if (
    haystack.includes('register') ||
    haystack.includes('|a') ||
    haystack.includes('|f') ||
    haystack.includes('|t') ||
    haystack.includes('|e')
  ) {
    return 'register';
  }
  if (haystack.includes('foundation') || haystack.includes('drive') || /f[1-7]/.test(haystack)) {
    return 'foundation';
  }
  if (haystack.includes('domain') || haystack.includes('operational') || haystack.includes('cognitive')) {
    return 'domain';
  }
  if (haystack.includes('noetic') || /\^\d/.test(haystack)) {
    return 'noetic';
  }
  if (haystack.includes('decoder') || haystack.includes('logit') || haystack.includes('lm')) {
    return 'decoder';
  }
  if (haystack.includes('output') || haystack.includes('generation')) {
    return 'output';
  }
  if (commit.parent_node_id === null || commit.node_kind === 'user_prompt') {
    return 'input';
  }
  return 'decoder';
}

function regionForNode(node: ThoughtTreeNode): RegionKey {
  const haystack = textHaystack(node.kind, node.role, node.label, node.text, node.axis_attrs);
  if (haystack.includes('user_prompt') || haystack.includes('input')) return 'input';
  if (haystack.includes('identifier') || haystack.includes('copy')) return 'copy';
  if (haystack.includes('slot') || haystack.includes('domain')) return 'domain';
  if (haystack.includes('confidence')) return 'output';
  if (haystack.includes('model_generation') || haystack.includes('output')) return 'decoder';
  if (haystack.includes('nl_bridge') || haystack.includes('cas_expression')) return 'noetic';
  return 'decoder';
}

function evidenceMode(
  commits: readonly SggsCommit[],
  runtimeReady: boolean,
  tree: AtlasTraceThoughtTree,
): EvidenceMode {
  const headCount = commits.filter(isHeadCommit).length;
  if (runtimeReady && headCount > 0) return 'real_activation';
  if (headCount > 0) return 'fallback_stream';
  if (tree.node_count > 1) return 'derived_trace';
  return 'stub_demo';
}

function evidenceLabel(mode: EvidenceMode): string {
  if (mode === 'real_activation') return 'REAL MODE 7 STREAM';
  if (mode === 'fallback_stream') return 'FALLBACK STREAM';
  if (mode === 'derived_trace') return 'DERIVED TRACE';
  return 'DEMO MAP';
}

function evidenceHelp(mode: EvidenceMode): string {
  if (mode === 'real_activation') {
    return 'Live events are coming from the configured CAS Native predictor.';
  }
  if (mode === 'fallback_stream') {
    return 'The live stream is active, but the runtime reports fallback or partial evidence.';
  }
  if (mode === 'derived_trace') {
    return 'This view is derived from the current trace graph, not raw activation tensors.';
  }
  return 'This idle view shows the intended neural path before a stream starts.';
}

function makeRegionStates(
  tree: AtlasTraceThoughtTree,
  commits: readonly SggsCommit[],
  selectedNodeId: string | null | undefined,
): RegionState[] {
  const counts = new Map<RegionKey, number>();
  const selectedRegions = new Set<RegionKey>();

  for (const commit of commits) {
    if (!isHeadCommit(commit)) continue;
    const region = regionForHeadCommit(commit);
    counts.set(region, (counts.get(region) ?? 0) + 1);
    if (commit.node_id === selectedNodeId) selectedRegions.add(region);
  }

  if (commits.filter(isHeadCommit).length === 0) {
    for (const node of tree.nodes) {
      const region = regionForNode(node);
      counts.set(region, (counts.get(region) ?? 0) + 1);
      if (node.id === selectedNodeId) selectedRegions.add(region);
    }
  }

  const maxCount = Math.max(1, ...Array.from(counts.values()));
  return REGIONS.map((region) => {
    const count = counts.get(region.key) ?? 0;
    const score = count === 0 ? 0.16 : 0.34 + 0.66 * (count / maxCount);
    return {
      ...region,
      count,
      score,
      selected: selectedRegions.has(region.key),
    };
  });
}

function makeMarkers(
  tree: AtlasTraceThoughtTree,
  commits: readonly SggsCommit[],
  selectedNodeId: string | null | undefined,
): ActivityMarker[] {
  const headCommits = commits.filter(isHeadCommit);
  const source =
    headCommits.length > 0
      ? headCommits.slice(-18).map((commit, index) => {
          const region = regionForHeadCommit(commit);
          return {
            id: `commit-${commit.turn_id}-${commit.head_index}-${commit.node_id}`,
            nodeId: commit.node_id,
            label: commit.node_label,
            detail: commit.head_name.replace(/_/g, ' '),
            region,
            index,
          };
        })
      : tree.nodes.slice(0, 18).map((node, index) => {
          const region = regionForNode(node);
          return {
            id: `node-${node.id}`,
            nodeId: node.id,
            label: node.label,
            detail: node.kind.replace(/_/g, ' '),
            region,
            index,
          };
        });

  return source.flatMap((entry) => {
    const region = REGION_BY_KEY.get(entry.region);
    if (!region) return [];
    const angle = (entry.index % 7) * 0.86 + 0.4;
    const radius = 0.32 + (entry.index % 3) * 0.12;
    return [
      {
        ...entry,
        x: region.cx + Math.cos(angle) * region.rx * radius,
        y: region.cy + Math.sin(angle) * region.ry * radius,
        color: region.color,
        selected: entry.nodeId === selectedNodeId,
      },
    ];
  });
}

function selectedSummary(
  tree: AtlasTraceThoughtTree,
  commits: readonly SggsCommit[],
  selectedNodeId: string | null | undefined,
): { label: string; detail: string; region: string; source: string } {
  const selectedCommit = commits.filter(isHeadCommit).find((commit) => commit.node_id === selectedNodeId);
  if (selectedCommit) {
    const region = REGION_BY_KEY.get(regionForHeadCommit(selectedCommit));
    return {
      label: selectedCommit.node_label,
      detail: selectedCommit.head_name.replace(/_/g, ' '),
      region: region?.label ?? 'Network Region',
      source: 'Mode 7 stream commit',
    };
  }
  const selectedNode = tree.nodes.find((node) => node.id === selectedNodeId) ?? tree.nodes[0];
  if (selectedNode) {
    const region = REGION_BY_KEY.get(regionForNode(selectedNode));
    return {
      label: selectedNode.label,
      detail: selectedNode.kind.replace(/_/g, ' '),
      region: region?.label ?? 'Trace Region',
      source: 'Trace graph node',
    };
  }
  return {
    label: 'No node selected',
    detail: 'Start a Mode 7 stream or select a marker.',
    region: 'Idle',
    source: 'No evidence selected',
  };
}

export function NeuralActivityMap({
  tree,
  commits,
  selectedNodeId,
  runtimeReady = false,
  onSelectNode,
  className,
}: NeuralActivityMapProps) {
  const mode = useMemo(
    () => evidenceMode(commits, runtimeReady, tree),
    [commits, runtimeReady, tree],
  );
  const regions = useMemo(
    () => makeRegionStates(tree, commits, selectedNodeId),
    [commits, selectedNodeId, tree],
  );
  const markers = useMemo(
    () => makeMarkers(tree, commits, selectedNodeId),
    [commits, selectedNodeId, tree],
  );
  const summary = useMemo(
    () => selectedSummary(tree, commits, selectedNodeId),
    [commits, selectedNodeId, tree],
  );
  const activeRegions = regions.filter((region) => region.count > 0).length;
  const headCommits = commits.filter(isHeadCommit);
  const activateNode = (nodeId: string) => {
    onSelectNode?.(nodeId);
  };
  const activateRegion = (regionKey: RegionKey) => {
    const marker = markers.find((candidate) => candidate.region === regionKey);
    if (marker) activateNode(marker.nodeId);
  };
  const onActivateKey = (event: KeyboardEvent, activate: () => void) => {
    if (event.key !== 'Enter' && event.key !== ' ') return;
    event.preventDefault();
    activate();
  };

  return (
    <section
      className={[
        'overflow-hidden rounded-lg border border-cyan-400/20 bg-slate-950/80',
        'shadow-[0_0_42px_rgba(34,211,238,0.10)]',
        className ?? '',
      ]
        .filter(Boolean)
        .join(' ')}
      data-testid="neural-activity-map"
    >
      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-white/[0.06] px-4 py-3">
        <div>
          <div className="font-mono text-[10px] uppercase tracking-[0.22em] text-cyan-300">
            CAS Neural Activity Map
          </div>
          <h2 className="mt-1 text-lg font-semibold text-slate-100">
            Watch the thought move through the model
          </h2>
          <p className="mt-1 max-w-2xl text-sm leading-relaxed text-slate-400">
            Brain-like, not anatomical: this maps CAS Native components and trace
            evidence into a living computation view.
          </p>
        </div>
        <div className="rounded-lg border border-cyan-300/20 bg-cyan-500/10 px-3 py-2 text-right">
          <div className="font-mono text-[10px] uppercase tracking-wider text-cyan-200">
            {evidenceLabel(mode)}
          </div>
          <div className="mt-1 text-xs text-slate-300">{evidenceHelp(mode)}</div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-0 lg:grid-cols-[minmax(0,1fr)_310px]">
        <div className="relative min-h-[470px] bg-[radial-gradient(circle_at_50%_45%,rgba(14,165,233,0.16),transparent_52%),radial-gradient(circle_at_72%_38%,rgba(168,85,247,0.12),transparent_45%)]">
          <svg
            viewBox="0 0 920 500"
            role="img"
            aria-label="CAS Neural Activity Map"
            className="h-full min-h-[470px] w-full"
          >
            <defs>
              <filter id="neural-glow" x="-60%" y="-60%" width="220%" height="220%">
                <feGaussianBlur stdDeviation="8" result="blur" />
                <feMerge>
                  <feMergeNode in="blur" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
              <linearGradient id="brain-shell" x1="0" x2="1" y1="0" y2="1">
                <stop offset="0%" stopColor="#0f172a" stopOpacity="0.42" />
                <stop offset="55%" stopColor="#164e63" stopOpacity="0.18" />
                <stop offset="100%" stopColor="#020617" stopOpacity="0.62" />
              </linearGradient>
            </defs>

            <path
              d="M88 270 C92 112 230 54 356 82 C422 26 560 36 624 98 C750 78 850 164 846 292 C842 416 720 458 600 424 C526 480 390 468 320 414 C202 432 82 392 88 270Z"
              fill="url(#brain-shell)"
              stroke="#38bdf8"
              strokeOpacity="0.18"
              strokeWidth="2"
            />
            <path
              d="M452 84 C430 144 430 218 456 274 C482 334 474 390 434 438"
              fill="none"
              stroke="#67e8f9"
              strokeDasharray="8 12"
              strokeOpacity="0.16"
              strokeWidth="2"
            />

            {PIPELINE.map(([fromKey, toKey]) => {
              const from = REGION_BY_KEY.get(fromKey)!;
              const to = REGION_BY_KEY.get(toKey)!;
              const fromActive = regions.find((region) => region.key === fromKey)?.count ?? 0;
              const toActive = regions.find((region) => region.key === toKey)?.count ?? 0;
              const active = fromActive > 0 || toActive > 0;
              const midX = (from.cx + to.cx) / 2;
              const midY = (from.cy + to.cy) / 2 - 28;
              return (
                <path
                  key={`${fromKey}-${toKey}`}
                  d={`M ${from.cx} ${from.cy} Q ${midX} ${midY} ${to.cx} ${to.cy}`}
                  fill="none"
                  stroke={active ? to.color : '#334155'}
                  strokeWidth={active ? 3.4 : 1.4}
                  strokeOpacity={active ? 0.64 : 0.24}
                  strokeDasharray={active ? '14 10' : '3 8'}
                  filter={active ? 'url(#neural-glow)' : undefined}
                >
                  {active && (
                    <animate
                      attributeName="stroke-dashoffset"
                      from="80"
                      to="0"
                      dur="2.2s"
                      repeatCount="indefinite"
                    />
                  )}
                </path>
              );
            })}

            {regions.map((region) => {
              const opacity = 0.16 + region.score * 0.62;
              const strokeWidth = region.selected ? 4.2 : region.count > 0 ? 2.8 : 1.4;
              return (
                <g
                  key={region.key}
                  tabIndex={0}
                  role="button"
                  aria-label={`Select region ${region.label}`}
                  onClick={() => activateRegion(region.key)}
                  onKeyDown={(event) => onActivateKey(event, () => activateRegion(region.key))}
                  className="cursor-pointer outline-none"
                >
                  <ellipse
                    cx={region.cx}
                    cy={region.cy}
                    rx={region.rx}
                    ry={region.ry}
                    fill={region.color}
                    fillOpacity={opacity}
                    stroke={region.selected ? '#f8fafc' : region.color}
                    strokeWidth={strokeWidth}
                    strokeOpacity={region.count > 0 ? 0.9 : 0.35}
                    filter={region.count > 0 ? 'url(#neural-glow)' : undefined}
                  />
                  {region.count > 0 && (
                    <ellipse
                      cx={region.cx}
                      cy={region.cy}
                      rx={region.rx + 7}
                      ry={region.ry + 7}
                      fill="none"
                      stroke={region.color}
                      strokeOpacity="0.22"
                      strokeWidth="8"
                    >
                      <animate
                        attributeName="stroke-opacity"
                        values="0.14;0.44;0.14"
                        dur="2.4s"
                        repeatCount="indefinite"
                      />
                    </ellipse>
                  )}
                  <text
                    x={region.cx}
                    y={region.cy - 4}
                    textAnchor="middle"
                    className="select-none fill-slate-50 text-[17px] font-bold"
                  >
                    {region.label}
                  </text>
                  <text
                    x={region.cx}
                    y={region.cy + 20}
                    textAnchor="middle"
                    className="select-none fill-slate-300 text-[11px]"
                  >
                    {region.count > 0 ? `${region.count} signals` : 'idle'}
                  </text>
                </g>
              );
            })}

            {markers.map((marker) => (
              <g
                key={marker.id}
                tabIndex={0}
                role="button"
                aria-label={`Select ${marker.label}`}
                onClick={() => activateNode(marker.nodeId)}
                onKeyDown={(event) => onActivateKey(event, () => activateNode(marker.nodeId))}
                className="cursor-pointer outline-none"
              >
                <circle
                  cx={marker.x}
                  cy={marker.y}
                  r={marker.selected ? 10 : 7}
                  fill={marker.selected ? '#f8fafc' : marker.color}
                  stroke={marker.color}
                  strokeWidth={marker.selected ? 5 : 2}
                  filter="url(#neural-glow)"
                />
                <title>{`${marker.label} - ${marker.detail}`}</title>
              </g>
            ))}
          </svg>

          <div className="absolute bottom-3 left-3 right-3 flex flex-wrap items-center justify-between gap-2 rounded-lg border border-white/[0.08] bg-black/55 px-3 py-2 text-xs text-slate-300 backdrop-blur-sm">
            <span>
              {activeRegions} regions active | {headCommits.length} head commits | {tree.node_count} trace nodes
            </span>
            <span className="font-mono text-[10px] uppercase tracking-wider text-cyan-300">
              click a region or pulse marker
            </span>
          </div>
        </div>

        <aside className="border-t border-white/[0.06] bg-black/25 p-4 lg:border-l lg:border-t-0">
          <div className="font-mono text-[10px] uppercase tracking-wider text-cyan-300">
            Selected Evidence
          </div>
          <h3 className="mt-2 text-lg font-semibold text-slate-100">{summary.label}</h3>
          <p className="mt-2 text-sm leading-relaxed text-slate-400">{summary.detail}</p>

          <dl className="mt-5 space-y-3 text-sm">
            <div className="rounded border border-white/[0.06] bg-white/[0.03] p-3">
              <dt className="font-mono text-[10px] uppercase tracking-wider text-slate-500">
                Region
              </dt>
              <dd className="mt-1 text-slate-100">{summary.region}</dd>
            </div>
            <div className="rounded border border-white/[0.06] bg-white/[0.03] p-3">
              <dt className="font-mono text-[10px] uppercase tracking-wider text-slate-500">
                Evidence source
              </dt>
              <dd className="mt-1 text-slate-100">{summary.source}</dd>
            </div>
            <div className="rounded border border-white/[0.06] bg-white/[0.03] p-3">
              <dt className="font-mono text-[10px] uppercase tracking-wider text-slate-500">
                Current mode
              </dt>
              <dd className="mt-1 text-slate-100">{evidenceLabel(mode)}</dd>
            </div>
          </dl>

          <div className="mt-5 rounded-lg border border-cyan-300/15 bg-cyan-500/[0.05] p-3">
            <div className="font-mono text-[10px] uppercase tracking-wider text-cyan-300">
              Demo claim
            </div>
            <p className="mt-2 text-sm leading-relaxed text-slate-300">
              CAS exposes a turn as an inspectable object: meaning, syntax,
              trace provenance, and model evidence can be watched as the answer
              forms.
            </p>
          </div>
        </aside>
      </div>
    </section>
  );
}

export default NeuralActivityMap;
