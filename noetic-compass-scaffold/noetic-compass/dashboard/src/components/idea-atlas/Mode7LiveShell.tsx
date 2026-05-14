import {
  lazy,
  Suspense,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type FormEvent,
} from 'react';
import {
  authenticatedSggsEventSource,
  mode7LiveUrl,
} from '../../api/sggs';
import {
  useSggsLiveTree,
  type SggsCommit,
  type SggsStreamStatus,
} from '../../lib/sggs_stream';
import type {
  AtlasTraceThoughtTree,
  ThoughtTreeEdge,
  ThoughtTreeNode,
  ThoughtTreeRootNode,
} from '../../lib/trace';
import { SggsErrorBoundary } from './SggsErrorBoundary';

const SggsScene = lazy(() =>
  import('./SggsScene').then((m) => ({
    default: m.SggsScene,
  })),
);

interface Mode7Request {
  prompt: string;
  source: string;
  runId: number;
}

interface Mode7EventView {
  id: string;
  nodeId: string | null;
  kind: string;
  label: string;
  detail: string;
}

type SggsHeadCommitView = Extract<SggsCommit, { kind: 'head_commit' }>;
type SggsTurnStartCommitView = Extract<SggsCommit, { kind: 'turn_start' }>;

interface AttrField {
  label: string;
  keys: readonly string[];
}

interface DetailItem {
  label: string;
  value: string;
}

interface DetailGroup {
  title: string;
  items: DetailItem[];
  empty: string;
}

interface TrailView {
  id: string;
  nodeId: string | null;
  label: string;
  detail: string;
  selected: boolean;
}

const DEFAULT_PROMPT =
  'Trace the first principles behind a stakeholder decision and expose the Mode 7 network attribution path as evidence arrives.';
const DEFAULT_SOURCE = 'CAS Native AI traceability stream';

const TOKEN_DETAIL_FIELDS: readonly AttrField[] = [
  {
    label: 'load-bearing tokens',
    keys: ['load_bearing_tokens', 'loadBearingTokens'],
  },
  {
    label: 'decoded token',
    keys: ['decoded_token_str', 'token_str', 'token', 'decoded_token'],
  },
  {
    label: 'token id',
    keys: ['decoded_token_id', 'token_id'],
  },
  {
    label: 'position',
    keys: ['position', 'output_position', 'input_position'],
  },
  {
    label: 'slot type',
    keys: ['slot_type', 'emission_route'],
  },
  {
    label: 'copy source',
    keys: ['copy_source_index', 'best_src_position', 'copy_source_indices'],
  },
  {
    label: 'token count',
    keys: ['n_tokens', 'token_count'],
  },
  {
    label: 'source tokens',
    keys: ['source_tokens', 'bpe_tokens', 'tokens'],
  },
] as const;

const LAYER_DETAIL_FIELDS: readonly AttrField[] = [
  {
    label: 'activation layers',
    keys: ['activation_layers', 'layer_activations'],
  },
  {
    label: 'activation hooks',
    keys: ['activation_hooks', 'hook_status'],
  },
  {
    label: 'layer l2',
    keys: ['layer_l2', 'encoder_layer_l2', 'decoder_layer_l2'],
  },
  {
    label: 'hidden l2',
    keys: ['decoder_hidden_l2', 'hidden_l2'],
  },
  {
    label: 'simplex',
    keys: ['simplex_pooled', 'simplex_trajectory_summary'],
  },
  {
    label: 'noetic',
    keys: ['noetic', 'dominant_noetic', 'dominant_noetic_name'],
  },
  {
    label: 'domain',
    keys: ['domain', 'dominant_domain', 'dominant_domain_name'],
  },
  {
    label: 'drive',
    keys: ['drive', 'dominant_drive'],
  },
  {
    label: 'register',
    keys: ['register', 'dominant_register'],
  },
] as const;

const LOGIT_DETAIL_FIELDS: readonly AttrField[] = [
  {
    label: 'head attribution',
    keys: ['node_relevant_head_attribution', 'per_head_attribution'],
  },
  {
    label: 'logits summary',
    keys: ['logits_summary', 'logits_copy_distribution_summary'],
  },
  {
    label: 'copy summary',
    keys: ['copy_distribution_summary'],
  },
  {
    label: 'lm logits',
    keys: ['lm_logits_top5', 'lm_logits_top5_per_position', 'lm_logits'],
  },
  {
    label: 'slot logits',
    keys: ['slot_type_top3', 'slot_type_logits', 'slot_type_confidence'],
  },
  {
    label: 'copy probabilities',
    keys: ['p_copy_top5', 'p_copy_top5_per_position', 'p_copy'],
  },
  {
    label: 'copy entropy',
    keys: ['p_copy_entropy', 'p_copy_entropy_per_position'],
  },
  {
    label: 'confidence',
    keys: ['confidence', 'band'],
  },
] as const;

const KNOWN_AXIS_ATTR_KEYS = new Set<string>([
  ...TOKEN_DETAIL_FIELDS.flatMap((field) => field.keys),
  ...LAYER_DETAIL_FIELDS.flatMap((field) => field.keys),
  ...LOGIT_DETAIL_FIELDS.flatMap((field) => field.keys),
  'node_key',
  'role',
  'normalized_label',
  'text',
  'mode7_semantics',
  'structural_commit_linkage',
  'mechanistic_diagnostics',
  'domain_descent_attention',
]);

function shortLabel(value: string, fallback: string, max = 54): string {
  const trimmed = value.trim() || fallback;
  return trimmed.length > max ? `${trimmed.slice(0, max - 3)}...` : trimmed;
}

function isPlainRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function isHeadCommit(commit: SggsCommit): commit is SggsHeadCommitView {
  return commit.kind === 'head_commit';
}

function isTurnStartCommit(
  commit: SggsCommit,
): commit is SggsTurnStartCommitView {
  return commit.kind === 'turn_start';
}

function hasAttrValue(value: unknown): boolean {
  if (value === null || value === undefined) return false;
  if (typeof value === 'string') return value.trim().length > 0;
  if (Array.isArray(value)) return value.length > 0;
  if (isPlainRecord(value)) return Object.keys(value).length > 0;
  return true;
}

function formatAttrValue(value: unknown, max = 120): string {
  let text: string;
  if (typeof value === 'string') {
    text = value;
  } else if (typeof value === 'number' || typeof value === 'boolean') {
    text = String(value);
  } else if (Array.isArray(value)) {
    const visible = value
      .slice(0, 5)
      .map((item) => formatAttrValue(item, 48))
      .join(', ');
    text = value.length > 5 ? `[${visible}, +${value.length - 5} more]` : `[${visible}]`;
  } else if (isPlainRecord(value)) {
    try {
      text = JSON.stringify(value);
    } catch {
      text = String(value);
    }
  } else if (value === null || value === undefined) {
    text = 'not emitted';
  } else {
    text = String(value);
  }
  const trimmed = text.trim() || 'empty';
  return trimmed.length > max ? `${trimmed.slice(0, max - 3)}...` : trimmed;
}

function formatAttrLabel(key: string): string {
  return key.replace(/_/g, ' ');
}

function attrItems(
  attrs: Record<string, unknown>,
  fields: readonly AttrField[],
): DetailItem[] {
  return fields.flatMap((field) => {
    const key = field.keys.find((candidate) => hasAttrValue(attrs[candidate]));
    if (!key) return [];
    return [{ label: field.label, value: formatAttrValue(attrs[key]) }];
  });
}

function remainingAttrItems(attrs: Record<string, unknown>): DetailItem[] {
  return Object.entries(attrs)
    .filter(([key, value]) => !KNOWN_AXIS_ATTR_KEYS.has(key) && hasAttrValue(value))
    .slice(0, 8)
    .map(([key, value]) => ({
      label: formatAttrLabel(key),
      value: formatAttrValue(value),
    }));
}

function buildSymbolicTrail(
  tree: AtlasTraceThoughtTree,
  selectedNodeId: string | null,
): TrailView[] {
  const nodesById = new Map(tree.nodes.map((node) => [node.id, node]));
  const rootId = tree.root.id ?? tree.nodes[0]?.id ?? null;
  const targetId =
    selectedNodeId && nodesById.has(selectedNodeId) ? selectedNodeId : rootId;
  if (!targetId) return [];

  const parentByTarget = new Map<string, string>();
  for (const edge of tree.edges) {
    if (!parentByTarget.has(edge.target)) {
      parentByTarget.set(edge.target, edge.source);
    }
  }

  const ids: string[] = [];
  const seen = new Set<string>();
  let cursor: string | undefined = targetId;
  while (cursor && !seen.has(cursor)) {
    seen.add(cursor);
    ids.push(cursor);
    if (cursor === rootId) break;
    cursor = parentByTarget.get(cursor);
  }

  return ids.reverse().flatMap((id, index) => {
    const node = nodesById.get(id);
    if (!node) return [];
    return [
      {
        id: `symbolic-${id}`,
        nodeId: id,
        label: `${index + 1}. ${node.label}`,
        detail: `${formatAttrLabel(node.kind)} / ${formatAttrLabel(node.role)}`,
        selected: id === targetId,
      },
    ];
  });
}

function buildMechanisticTrail(
  headCommits: readonly SggsHeadCommitView[],
  selectedNodeId: string | null,
): TrailView[] {
  const selectedIndex = headCommits.findIndex(
    (commit) => commit.node_id === selectedNodeId,
  );
  const visible =
    selectedIndex >= 0
      ? headCommits.slice(Math.max(0, selectedIndex - 5), selectedIndex + 1)
      : headCommits.slice(-6);

  return visible.map((commit) => ({
    id: `mechanistic-${commit.head_index}-${commit.node_id}`,
    nodeId: commit.node_id,
    label: `#${commit.head_index} ${formatAttrLabel(commit.head_name)}`,
    detail: `${formatAttrLabel(commit.node_kind)} / ${commit.node_label}`,
    selected: commit.node_id === selectedNodeId,
  }));
}

function rootNode(
  id: string,
  kind: string,
  role: string,
  label: string,
  text: string,
  children: ThoughtTreeRootNode[] = [],
): ThoughtTreeRootNode {
  return {
    id,
    node_key: `${kind}|${role}|${label}`,
    kind,
    role,
    label,
    normalized_label: label.toLowerCase(),
    text,
    children,
  };
}

function flattenTree(root: ThoughtTreeRootNode): {
  nodes: ThoughtTreeNode[];
  edges: ThoughtTreeEdge[];
} {
  const nodes: ThoughtTreeNode[] = [];
  const edges: ThoughtTreeEdge[] = [];

  function visit(node: ThoughtTreeRootNode, parent: ThoughtTreeRootNode | null) {
    const nodeId = node.id ?? node.node_key ?? node.label;
    const nodeKey = node.node_key ?? nodeId;
    if (!nodeId) return;
    nodes.push({
      id: nodeId,
      node_key: nodeKey,
      kind: node.kind,
      role: node.role,
      label: node.label,
      normalized_label: node.normalized_label,
      axis_attrs: node.axis_attrs,
      text: node.text,
    });
    const parentId = parent?.id ?? parent?.node_key;
    const parentKey = parent?.node_key ?? parentId;
    if (parentId && parentKey) {
      edges.push({
        id: `idle-${parentId}-${nodeId}`,
        edge_key: `${parentKey}->${nodeKey}`,
        source: parentId,
        target: nodeId,
        source_key: parentKey,
        target_key: nodeKey,
        kind: 'mode7_source',
      });
    }
    for (const child of node.children ?? []) {
      visit(child, node);
    }
  }

  visit(root, null);
  return { nodes, edges };
}

function buildIdleTree(prompt: string, source: string): AtlasTraceThoughtTree {
  const root = rootNode(
    'n0',
    'user_prompt',
    'live_prompt',
    shortLabel(prompt, 'Mode 7 trace prompt'),
    prompt.trim() || DEFAULT_PROMPT,
    [
      rootNode(
        'mode7-source',
        'nl_bridge',
        'cas_native_source',
        shortLabel(source, 'CAS Native AI source'),
        source.trim() || DEFAULT_SOURCE,
      ),
    ],
  );
  const { nodes, edges } = flattenTree(root);
  return {
    root,
    nodes,
    edges,
    node_count: nodes.length,
    edge_count: edges.length,
  };
}

function requestPrompt(prompt: string, source: string): string {
  const cleanPrompt = prompt.trim() || DEFAULT_PROMPT;
  const cleanSource = source.trim();
  if (!cleanSource || cleanSource === DEFAULT_SOURCE) return cleanPrompt;
  return `${cleanPrompt}\n\nSource: ${cleanSource}`;
}

function expressionFromSource(source: string): string | undefined {
  const trimmed = source.trim();
  if (!trimmed || trimmed === DEFAULT_SOURCE) return undefined;
  return /[<>{}_^]|^[A-Z]{2}-/.test(trimmed) ? trimmed : undefined;
}

function statusLabel(status: SggsStreamStatus, enabled: boolean, endedAt: string | null): string {
  if (enabled && status === 'connecting') return 'Connecting';
  if (enabled && status === 'open') return 'Live';
  if (endedAt) return 'Complete';
  if (status === 'error') return 'Stream error';
  if (status === 'closed') return 'Stopped';
  return 'Ready';
}

function formatLiveTime(value: string | null): string {
  if (!value) return 'not started';
  try {
    return new Date(value).toLocaleTimeString(undefined, {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  } catch {
    return value;
  }
}

function commitEvent(commit: SggsCommit, index: number): Mode7EventView {
  if (commit.kind === 'turn_start') {
    return {
      id: `${index}-${commit.kind}`,
      nodeId: 'n0',
      kind: 'turn start',
      label: 'CAS Native turn started',
      detail: commit.user_text,
    };
  }
  if (commit.kind === 'head_commit') {
    return {
      id: `${index}-${commit.node_id}`,
      nodeId: commit.node_id,
      kind: commit.node_kind.replace(/_/g, ' '),
      label: commit.node_label,
      detail: commit.head_name.replace(/_/g, ' '),
    };
  }
  if (commit.kind === 'edge_commit') {
    return {
      id: `${index}-${commit.edge_id}`,
      nodeId: commit.target_node_id,
      kind: 'edge',
      label: `${commit.source_node_id} -> ${commit.target_node_id}`,
      detail: commit.edge_kind.replace(/_/g, ' '),
    };
  }
  if (commit.kind === 'turn_end') {
    return {
      id: `${index}-${commit.final_trace_id}`,
      nodeId: null,
      kind: 'turn end',
      label: 'Trace complete',
      detail: `${commit.total_heads} heads in ${commit.duration_ms} ms`,
    };
  }
  return {
    id: `${index}-${commit.kind}`,
    nodeId: null,
    kind: commit.kind,
    label: commit.kind === 'warning' ? commit.message : commit.code,
    detail: commit.kind === 'warning' ? commit.severity : commit.message,
  };
}

function FullscreenIcon({ active }: { active: boolean }) {
  if (active) {
    return (
      <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M8 3v3a2 2 0 0 1-2 2H3" />
        <path d="M21 8h-3a2 2 0 0 1-2-2V3" />
        <path d="M3 16h3a2 2 0 0 1 2 2v3" />
        <path d="M16 21v-3a2 2 0 0 1 2-2h3" />
      </svg>
    );
  }
  return (
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M3 7V5a2 2 0 0 1 2-2h2" />
      <path d="M17 3h2a2 2 0 0 1 2 2v2" />
      <path d="M21 17v2a2 2 0 0 1-2 2h-2" />
      <path d="M7 21H5a2 2 0 0 1-2-2v-2" />
    </svg>
  );
}

function TrailPanel({
  title,
  tone,
  items,
  empty,
  onSelectNode,
}: {
  title: string;
  tone: 'cyan' | 'violet';
  items: readonly TrailView[];
  empty: string;
  onSelectNode: (nodeId: string) => void;
}) {
  const toneClass = tone === 'cyan' ? 'text-cyan-300' : 'text-violet-300';
  const selectedClass =
    tone === 'cyan'
      ? 'border-cyan-300/40 bg-cyan-500/10'
      : 'border-violet-300/40 bg-violet-500/10';

  return (
    <section className="rounded-lg border border-white/[0.06] bg-black/30 p-4">
      <div className={`font-mono text-[10px] uppercase tracking-wider ${toneClass}`}>
        {title}
      </div>
      <div className="mt-3 divide-y divide-white/[0.06]">
        {items.length === 0 ? (
          <div className="py-2 text-sm text-slate-500">{empty}</div>
        ) : (
          items.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => item.nodeId && onSelectNode(item.nodeId)}
              className={`w-full border-l-2 py-2 pl-3 pr-1 text-left transition-colors hover:bg-white/[0.04] ${
                item.selected
                  ? selectedClass
                  : 'border-transparent bg-transparent'
              }`}
            >
              <div className="text-sm text-slate-100">{item.label}</div>
              <div className="mt-1 font-mono text-[10px] uppercase tracking-wider text-slate-500">
                {item.detail}
              </div>
            </button>
          ))
        )}
      </div>
    </section>
  );
}

function DetailGroupPanel({ group }: { group: DetailGroup }) {
  return (
    <div>
      <div className="font-mono text-[10px] uppercase tracking-wider text-slate-500">
        {group.title}
      </div>
      {group.items.length === 0 ? (
        <div className="mt-2 text-xs text-slate-600">{group.empty}</div>
      ) : (
        <dl className="mt-2 divide-y divide-white/[0.06] text-xs">
          {group.items.map((item) => (
            <div
              key={`${group.title}-${item.label}`}
              className="grid grid-cols-[96px_minmax(0,1fr)] gap-3 py-2"
            >
              <dt className="font-mono uppercase tracking-wider text-slate-500">
                {item.label}
              </dt>
              <dd className="break-words font-mono text-slate-300">{item.value}</dd>
            </div>
          ))}
        </dl>
      )}
    </div>
  );
}

export function Mode7LiveShell() {
  const [promptDraft, setPromptDraft] = useState(DEFAULT_PROMPT);
  const [sourceDraft, setSourceDraft] = useState(DEFAULT_SOURCE);
  const [activeRequest, setActiveRequest] = useState<Mode7Request | null>(null);
  const [streamEnabled, setStreamEnabled] = useState(false);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>('n0');
  const [fullscreen, setFullscreen] = useState(false);
  const sceneShellRef = useRef<HTMLDivElement | null>(null);

  const streamUrl = useMemo(() => {
    const request = activeRequest ?? {
      prompt: promptDraft,
      source: sourceDraft,
      runId: 0,
    };
    const url = mode7LiveUrl({
      prompt: requestPrompt(request.prompt, request.source),
      expression: expressionFromSource(request.source),
      delayMs: 140,
    });
    return `${url}&run=${request.runId}`;
  }, [activeRequest, promptDraft, sourceDraft]);

  const stream = useSggsLiveTree({
    url: streamUrl,
    enabled: streamEnabled,
    eventSourceFactory: authenticatedSggsEventSource,
  });

  const displayPrompt = activeRequest?.prompt ?? promptDraft;
  const displaySource = activeRequest?.source ?? sourceDraft;
  const tree = stream.tree ?? buildIdleTree(displayPrompt, displaySource);
  const label = statusLabel(stream.status, streamEnabled, stream.state.endedAt);
  const isRunning =
    streamEnabled && (stream.status === 'connecting' || stream.status === 'open');

  const events = useMemo(
    () => stream.state.commits.map(commitEvent).slice(-12).reverse(),
    [stream.state.commits],
  );

  const selectedNode = useMemo(
    () => tree.nodes.find((node) => node.id === selectedNodeId) ?? null,
    [selectedNodeId, tree.nodes],
  );

  const headCommits = useMemo(
    () => stream.state.commits.filter(isHeadCommit),
    [stream.state.commits],
  );

  const turnStartCommit = useMemo(
    () => stream.state.commits.find(isTurnStartCommit) ?? null,
    [stream.state.commits],
  );

  const selectedHeadCommit = useMemo(
    () =>
      selectedNodeId
        ? headCommits.find((commit) => commit.node_id === selectedNodeId) ?? null
        : null,
    [headCommits, selectedNodeId],
  );

  const selectedCommitIndex = useMemo(() => {
    if (!selectedNodeId) return -1;
    return stream.state.commits.findIndex((commit) => {
      if (commit.kind === 'turn_start') return selectedNodeId === 'n0';
      return commit.kind === 'head_commit' && commit.node_id === selectedNodeId;
    });
  }, [selectedNodeId, stream.state.commits]);

  const selectedIncomingEdges = useMemo(
    () =>
      selectedNode
        ? tree.edges.filter((edge) => edge.target === selectedNode.id)
        : [],
    [selectedNode, tree.edges],
  );

  const selectedOutgoingEdges = useMemo(
    () =>
      selectedNode
        ? tree.edges.filter((edge) => edge.source === selectedNode.id)
        : [],
    [selectedNode, tree.edges],
  );

  const selectedAxisAttrs = useMemo(() => {
    const nodeAttrs = selectedNode?.axis_attrs;
    const headAttrs = selectedHeadCommit?.axis_attrs;
    return {
      ...(isPlainRecord(nodeAttrs) ? nodeAttrs : {}),
      ...(isPlainRecord(headAttrs) ? headAttrs : {}),
    };
  }, [selectedHeadCommit, selectedNode]);

  const symbolicTrail = useMemo(
    () => buildSymbolicTrail(tree, selectedNodeId),
    [selectedNodeId, tree],
  );

  const mechanisticTrail = useMemo(
    () => buildMechanisticTrail(headCommits, selectedNodeId),
    [headCommits, selectedNodeId],
  );

  const selectedDetailGroups = useMemo<DetailGroup[]>(() => {
    const parentNodeId =
      selectedHeadCommit?.parent_node_id ?? selectedIncomingEdges[0]?.source ?? null;
    const headItems: DetailItem[] = selectedHeadCommit
      ? [
          {
            label: 'head',
            value: formatAttrLabel(selectedHeadCommit.head_name),
          },
          {
            label: 'index',
            value: String(selectedHeadCommit.head_index),
          },
          {
            label: 'event',
            value:
              selectedCommitIndex >= 0 ? `#${selectedCommitIndex + 1}` : 'linked',
          },
          {
            label: 'kind',
            value: selectedHeadCommit.node_kind,
          },
        ]
      : selectedNode?.id === 'n0' && turnStartCommit
        ? [
            {
              label: 'event',
              value:
                selectedCommitIndex >= 0
                  ? `turn start #${selectedCommitIndex + 1}`
                  : 'turn start',
            },
            {
              label: 'turn',
              value: turnStartCommit.turn_id,
            },
            {
              label: 'created',
              value: formatLiveTime(turnStartCommit.created_at),
            },
          ]
        : [];

    const linkageItems: DetailItem[] = selectedNode
      ? [
          {
            label: 'node id',
            value: selectedNode.id,
          },
          {
            label: 'node key',
            value: selectedNode.node_key,
          },
          {
            label: 'parent',
            value: parentNodeId ?? 'root',
          },
          {
            label: 'incoming',
            value: String(selectedIncomingEdges.length),
          },
          {
            label: 'outgoing',
            value: String(selectedOutgoingEdges.length),
          },
          ...(stream.state.finalTraceId
            ? [
                {
                  label: 'trace',
                  value: stream.state.finalTraceId,
                },
              ]
            : []),
        ]
      : [];

    return [
      {
        title: 'Head Commit',
        items: headItems,
        empty: 'No head commit is linked to this node yet.',
      },
      {
        title: 'Tokens',
        items: attrItems(selectedAxisAttrs, TOKEN_DETAIL_FIELDS),
        empty: 'No token evidence emitted for this node.',
      },
      {
        title: 'Layers / State',
        items: attrItems(selectedAxisAttrs, LAYER_DETAIL_FIELDS),
        empty: 'No layer or state values emitted for this node.',
      },
      {
        title: 'Logits / Attribution',
        items: attrItems(selectedAxisAttrs, LOGIT_DETAIL_FIELDS),
        empty: 'No logits or attribution values emitted for this node.',
      },
      {
        title: 'Commit Linkage',
        items: linkageItems,
        empty: 'No graph linkage is selected.',
      },
      {
        title: 'Other Attributes',
        items: remainingAttrItems(selectedAxisAttrs),
        empty: 'No additional attributes emitted.',
      },
    ];
  }, [
    selectedAxisAttrs,
    selectedCommitIndex,
    selectedHeadCommit,
    selectedIncomingEdges,
    selectedNode,
    selectedOutgoingEdges,
    stream.state.finalTraceId,
    turnStartCommit,
  ]);

  useEffect(() => {
    if (selectedNodeId && tree.nodes.some((node) => node.id === selectedNodeId)) {
      return;
    }
    setSelectedNodeId(tree.root.id ?? tree.nodes[0]?.id ?? null);
  }, [selectedNodeId, tree]);

  useEffect(() => {
    const onChange = () => {
      setFullscreen(document.fullscreenElement === sceneShellRef.current);
    };
    document.addEventListener('fullscreenchange', onChange);
    return () => document.removeEventListener('fullscreenchange', onChange);
  }, []);

  const toggleFullscreen = useCallback(() => {
    const el = sceneShellRef.current;
    if (!el) return;
    if (document.fullscreenElement === el) {
      void document.exitFullscreen?.();
    } else {
      void el.requestFullscreen?.();
    }
  }, []);

  const handleStart = useCallback(
    (event?: FormEvent) => {
      event?.preventDefault();
      stream.reset();
      const nextRequest = {
        prompt: promptDraft.trim() || DEFAULT_PROMPT,
        source: sourceDraft.trim() || DEFAULT_SOURCE,
        runId: Date.now(),
      };
      setActiveRequest(nextRequest);
      setSelectedNodeId('n0');
      setStreamEnabled(true);
    },
    [promptDraft, sourceDraft, stream],
  );

  const handleStop = useCallback(() => {
    setStreamEnabled(false);
  }, []);

  return (
    <div className="flex-1 overflow-y-auto px-6 py-4">
      <div className="grid min-h-[640px] grid-cols-1 gap-4 xl:grid-cols-[360px_minmax(0,1fr)]">
        <aside className="flex flex-col gap-4">
          <section className="rounded-lg border border-cyan-400/20 bg-cyan-500/[0.04] p-4">
            <div className="mb-3 flex items-center justify-between gap-3">
              <div>
                <div className="font-mono text-[10px] uppercase tracking-wider text-cyan-300">
                  MODE 7
                </div>
                <h2 className="mt-1 font-sans text-lg font-semibold text-slate-100">
                  Network Attribution / Mechanistic Trace
                </h2>
              </div>
              <span
                className={`rounded border px-2 py-1 font-mono text-[10px] uppercase tracking-wider ${
                  label === 'Live'
                    ? 'border-emerald-400/40 bg-emerald-500/15 text-emerald-200'
                    : label === 'Connecting'
                      ? 'border-amber-400/40 bg-amber-500/15 text-amber-200'
                      : label === 'Stream error'
                        ? 'border-rose-400/40 bg-rose-500/15 text-rose-200'
                        : 'border-white/10 bg-white/[0.04] text-slate-300'
                }`}
              >
                {label}
              </span>
            </div>
            <p className="text-sm leading-relaxed text-slate-300">
              Mode 7 exposes the head commits, token evidence, layer state,
              logits, and trace links behind each CAS Native AI turn. The
              Living Thought Atlas is the SGGS witness viewport for that trace.
            </p>
          </section>

          <form
            onSubmit={handleStart}
            className="rounded-lg border border-white/[0.06] bg-black/30 p-4"
          >
            <label className="block font-mono text-[10px] uppercase tracking-wider text-slate-400">
              Prompt
            </label>
            <textarea
              value={promptDraft}
              onChange={(event) => setPromptDraft(event.target.value)}
              rows={6}
              className="mt-2 min-h-32 w-full resize-y rounded border border-white/[0.08] bg-black/40 px-3 py-2 font-sans text-sm leading-relaxed text-slate-100 placeholder:text-slate-600 focus:border-cyan-300/60 focus:outline-none"
              placeholder="Ask CAS Native AI to emit a Mode 7 trace..."
            />

            <label className="mt-4 block font-mono text-[10px] uppercase tracking-wider text-slate-400">
              Source / CAS expression
            </label>
            <input
              value={sourceDraft}
              onChange={(event) => setSourceDraft(event.target.value)}
              className="mt-2 w-full rounded border border-white/[0.08] bg-black/40 px-3 py-2 font-mono text-xs text-slate-100 placeholder:text-slate-600 focus:border-cyan-300/60 focus:outline-none"
              placeholder="Document name, transcript, or CO-2^C_{F2}"
            />

            <div className="mt-4 flex flex-wrap items-center gap-2">
              <button
                type="submit"
                disabled={isRunning}
                className="rounded border border-emerald-400/30 bg-emerald-500/10 px-3 py-2 font-mono text-xs text-emerald-200 transition-colors hover:bg-emerald-500/20 disabled:cursor-not-allowed disabled:opacity-40"
              >
                Start
              </button>
              <button
                type="button"
                onClick={handleStop}
                disabled={!isRunning}
                className="rounded border border-rose-400/30 bg-rose-500/10 px-3 py-2 font-mono text-xs text-rose-200 transition-colors hover:bg-rose-500/20 disabled:cursor-not-allowed disabled:opacity-40"
              >
                Stop
              </button>
            </div>
          </form>

          <section className="rounded-lg border border-white/[0.06] bg-black/30 p-4 font-mono text-[11px] text-slate-300">
            <div className="mb-3 text-[10px] uppercase tracking-wider text-slate-500">
              Live Status
            </div>
            <dl className="space-y-2">
              <div className="flex items-center justify-between gap-3">
                <dt className="text-slate-500">trace source</dt>
                <dd className="text-right text-cyan-200">{displaySource}</dd>
              </div>
              <div className="flex items-center justify-between gap-3">
                <dt className="text-slate-500">nodes</dt>
                <dd>{tree.node_count}</dd>
              </div>
              <div className="flex items-center justify-between gap-3">
                <dt className="text-slate-500">edges</dt>
                <dd>{tree.edge_count}</dd>
              </div>
              <div className="flex items-center justify-between gap-3">
                <dt className="text-slate-500">started</dt>
                <dd>{formatLiveTime(stream.state.startedAt)}</dd>
              </div>
              <div className="flex items-center justify-between gap-3">
                <dt className="text-slate-500">last event</dt>
                <dd>{formatLiveTime(stream.state.updatedAt)}</dd>
              </div>
            </dl>
            {(stream.state.warnings.length > 0 || stream.state.streamErrors.length > 0) && (
              <div className="mt-3 border-t border-white/[0.06] pt-3 font-sans text-xs leading-relaxed text-amber-200">
                {stream.state.streamErrors.at(-1) ??
                  stream.state.warnings.at(-1)?.message}
              </div>
            )}
          </section>
        </aside>

        <main className="flex min-w-0 flex-col gap-4">
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-violet-500/20 bg-violet-500/[0.05] px-4 py-3">
            <div>
              <div className="font-mono text-[10px] uppercase tracking-wider text-violet-300">
                Living Thought Atlas
              </div>
              <p className="mt-1 text-sm text-slate-300">
                {stream.state.finalTraceId
                  ? `final trace ${stream.state.finalTraceId}`
                  : 'Live SGGS witness for Mode 7 commits from CAS Native AI.'}
              </p>
            </div>
            <button
              type="button"
              onClick={toggleFullscreen}
              aria-label={fullscreen ? 'Exit fullscreen' : 'Enter fullscreen'}
              title={fullscreen ? 'Exit fullscreen' : 'Fullscreen the Living Thought Atlas'}
              className="flex h-9 w-9 items-center justify-center rounded-md border border-white/[0.08] bg-black/30 text-slate-200 transition-colors hover:bg-white/10 hover:text-white"
            >
              <FullscreenIcon active={fullscreen} />
            </button>
          </div>

          <div
            ref={sceneShellRef}
            style={{ height: fullscreen ? '100vh' : 560 }}
            className="relative min-h-[420px] overflow-hidden rounded-lg border-2 border-violet-500/30 bg-black/30"
          >
            <div className="pointer-events-none absolute left-3 top-3 z-20 rounded-md border border-cyan-300/20 bg-black/60 px-3 py-2 backdrop-blur-sm">
              <div className="font-mono text-[9px] uppercase tracking-wider text-cyan-300">
                Living Thought Atlas
              </div>
              <div className="mt-1 font-mono text-[11px] text-slate-200">
                SGGS live witness graph
              </div>
            </div>

            <button
              type="button"
              onClick={toggleFullscreen}
              aria-label={fullscreen ? 'Exit fullscreen' : 'Enter fullscreen'}
              title={fullscreen ? 'Exit fullscreen' : 'Fullscreen the Living Thought Atlas'}
              className="absolute right-3 top-3 z-20 flex h-9 w-9 items-center justify-center rounded-md border border-white/[0.08] bg-black/55 text-slate-200 backdrop-blur-sm transition-colors hover:bg-white/10 hover:text-white"
            >
              <FullscreenIcon active={fullscreen} />
            </button>

            <SggsErrorBoundary>
              <Suspense
                fallback={
                  <div className="absolute inset-0 flex items-center justify-center font-mono text-xs text-slate-400">
                    Loading SGGS witness viewport...
                  </div>
                }
              >
                <SggsScene
                  tree={tree}
                  onNodeClick={(node) => setSelectedNodeId(node.id)}
                  selectedNodeId={selectedNodeId}
                  className="h-full w-full"
                  fillParent
                />
              </Suspense>
            </SggsErrorBoundary>

            <div className="pointer-events-none absolute bottom-3 right-3 z-20 rounded-md bg-black/55 px-3 py-2 font-mono text-[10px] text-slate-300 backdrop-blur-sm">
              {tree.node_count} nodes | {tree.edge_count} edges | {stream.status}
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
            <TrailPanel
              title="Mode 3 Symbolic Trail"
              tone="cyan"
              items={symbolicTrail}
              empty="No symbolic commitments yet."
              onSelectNode={(nodeId) => setSelectedNodeId(nodeId)}
            />
            <TrailPanel
              title="Mode 7 Mechanistic Trail"
              tone="violet"
              items={mechanisticTrail}
              empty="No head commits yet."
              onSelectNode={(nodeId) => setSelectedNodeId(nodeId)}
            />
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1fr)_380px]">
            <section className="rounded-lg border border-white/[0.06] bg-black/30 p-4">
              <div className="mb-3 font-mono text-[10px] uppercase tracking-wider text-slate-500">
                Stream Events
              </div>
              <div className="space-y-2">
                {events.length === 0 ? (
                  <div className="rounded border border-white/[0.06] bg-white/[0.02] px-3 py-2 text-sm text-slate-500">
                    No live commits yet.
                  </div>
                ) : (
                  events.map((event) => (
                    <button
                      key={event.id}
                      type="button"
                      onClick={() => event.nodeId && setSelectedNodeId(event.nodeId)}
                      className={`w-full rounded border px-3 py-2 text-left transition-colors ${
                        selectedNodeId === event.nodeId
                          ? 'border-cyan-300/40 bg-cyan-500/10'
                          : 'border-white/[0.06] bg-white/[0.02] hover:bg-white/[0.05]'
                      }`}
                    >
                      <div className="font-mono text-[10px] uppercase tracking-wider text-cyan-300">
                        {event.kind}
                      </div>
                      <div className="mt-1 text-sm text-slate-100">{event.label}</div>
                      <div className="mt-1 text-xs leading-relaxed text-slate-500">
                        {event.detail}
                      </div>
                    </button>
                  ))
                )}
              </div>
            </section>

            <aside className="rounded-lg border border-white/[0.06] bg-black/30 p-4">
              <div className="font-mono text-[10px] uppercase tracking-wider text-slate-500">
                Selected Node Details
              </div>
              {selectedNode ? (
                <div className="mt-3 space-y-5 text-sm">
                  <div>
                    <div className="text-slate-100">{selectedNode.label}</div>
                    <div className="mt-1 font-mono text-[10px] uppercase tracking-wider text-cyan-300">
                      {selectedNode.kind} / {selectedNode.role}
                    </div>
                    {selectedNode.text && (
                      <div className="mt-2 text-xs leading-relaxed text-slate-400">
                        {selectedNode.text}
                      </div>
                    )}
                  </div>
                  {selectedDetailGroups.map((group) => (
                    <DetailGroupPanel key={group.title} group={group} />
                  ))}
                </div>
              ) : (
                <p className="mt-3 text-sm text-slate-500">
                  Select a commit in the Living Thought Atlas.
                </p>
              )}
            </aside>
          </div>
        </main>
      </div>
    </div>
  );
}
