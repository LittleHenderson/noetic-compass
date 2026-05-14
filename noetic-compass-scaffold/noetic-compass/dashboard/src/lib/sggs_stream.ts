/**
 * SGGS stream client — subscribes to a head-level structural-commit
 * Server-Sent Events stream from the CAS-Native inference server and
 * exposes parsed commits via a React hook.
 *
 * Wire format authority: `cas-native/inference/sggs_stream.py` and the
 * spec doc `docs/working/sggs_stream_protocol_2026_05_13.md`. Every
 * field on each commit kind mirrors a field there. If the Python
 * producer adds a field, this file should mirror it.
 *
 * Reconnect strategy: the browser-native `EventSource` does this
 * automatically. On reconnect, the browser sends the `Last-Event-ID`
 * header with the id of the last successfully-dispatched event. The
 * server is expected to resume the stream from after that id (replay
 * cache responsibility lives server-side; the client just exposes
 * `lastEventId` so a custom transport can read it on reconnect).
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import type {
  AtlasTraceThoughtTree,
  ThoughtTreeEdge,
  ThoughtTreeNode,
  ThoughtTreeRootNode,
} from './trace';

// ── Schema literal ───────────────────────────────────────────────────────

export const SGGS_STREAM_SCHEMA_VERSION = 'sggs_stream_v0' as const;
export type SggsStreamSchemaVersion = typeof SGGS_STREAM_SCHEMA_VERSION;

// ── Event kind literals (mirrors Python EVENT_KINDS) ─────────────────────

export const SGGS_EVENT_TURN_START = 'turn_start' as const;
export const SGGS_EVENT_HEAD_COMMIT = 'head_commit' as const;
export const SGGS_EVENT_EDGE_COMMIT = 'edge_commit' as const;
export const SGGS_EVENT_TURN_END = 'turn_end' as const;
export const SGGS_EVENT_WARNING = 'warning' as const;
export const SGGS_EVENT_ERROR = 'error' as const;

export type SggsEventKind =
  | typeof SGGS_EVENT_TURN_START
  | typeof SGGS_EVENT_HEAD_COMMIT
  | typeof SGGS_EVENT_EDGE_COMMIT
  | typeof SGGS_EVENT_TURN_END
  | typeof SGGS_EVENT_WARNING
  | typeof SGGS_EVENT_ERROR;

export const SGGS_EVENT_KINDS: readonly SggsEventKind[] = [
  SGGS_EVENT_TURN_START,
  SGGS_EVENT_HEAD_COMMIT,
  SGGS_EVENT_EDGE_COMMIT,
  SGGS_EVENT_TURN_END,
  SGGS_EVENT_WARNING,
  SGGS_EVENT_ERROR,
];

// ── Commit-kind discriminated union ──────────────────────────────────────

export interface SggsTurnStartCommit {
  kind: typeof SGGS_EVENT_TURN_START;
  turn_id: string;
  user_text: string;
  created_at: string;
  schema_version: SggsStreamSchemaVersion;
}

export interface SggsHeadCommit {
  kind: typeof SGGS_EVENT_HEAD_COMMIT;
  turn_id: string;
  head_index: number;
  head_name: string;
  node_id: string;
  node_kind: string;
  node_label: string;
  parent_node_id: string | null;
  axis_attrs: Record<string, unknown>;
  schema_version: SggsStreamSchemaVersion;
}

export interface SggsEdgeCommit {
  kind: typeof SGGS_EVENT_EDGE_COMMIT;
  turn_id: string;
  edge_id: string;
  source_node_id: string;
  target_node_id: string;
  edge_kind: string;
  schema_version: SggsStreamSchemaVersion;
}

export interface SggsTurnEndCommit {
  kind: typeof SGGS_EVENT_TURN_END;
  turn_id: string;
  final_trace_id: string;
  total_heads: number;
  duration_ms: number;
  ended_at: string;
  schema_version: SggsStreamSchemaVersion;
}

export interface SggsWarningCommit {
  kind: typeof SGGS_EVENT_WARNING;
  turn_id: string;
  severity: string;
  message: string;
  schema_version: SggsStreamSchemaVersion;
}

export interface SggsErrorCommit {
  kind: typeof SGGS_EVENT_ERROR;
  turn_id: string;
  code: string;
  message: string;
  schema_version: SggsStreamSchemaVersion;
}

export type SggsCommit =
  | SggsTurnStartCommit
  | SggsHeadCommit
  | SggsEdgeCommit
  | SggsTurnEndCommit
  | SggsWarningCommit
  | SggsErrorCommit;

// ── Connection status ────────────────────────────────────────────────────

export type SggsStreamStatus =
  | 'idle'
  | 'connecting'
  | 'open'
  | 'closed'
  | 'error';

// ── Hook public surface ──────────────────────────────────────────────────

export interface UseSggsStreamOptions {
  /** Endpoint URL the EventSource should subscribe to (e.g.
   * `/api/sggs/stream`). */
  url: string;
  /** Toggle connection without remounting the component. When false the
   * hook closes any existing connection and stays in `idle`. */
  enabled: boolean;
  /** Per-commit callback. Fires once per successfully-parsed event. */
  onCommit: (commit: SggsCommit) => void;
  /** Optional error callback. Fires for malformed JSON, unknown event
   * kinds, or transport errors. The stream stays open on parse errors
   * (a single bad event does not poison the stream); transport errors
   * surface here too but EventSource handles reconnect automatically. */
  onError?: (message: string) => void;
  /** Optional EventSource factory — tests inject `MockEventSource`. Defaults
   * to the browser-native `EventSource`. */
  eventSourceFactory?: (url: string) => EventSourceLike;
}

export interface UseSggsStreamReturn {
  status: SggsStreamStatus;
  lastEventId: string | null;
}

// -- Live tree adapter ------------------------------------------------------

export interface SggsLiveTreeState {
  turnId: string | null;
  userText: string | null;
  startedAt: string | null;
  endedAt: string | null;
  finalTraceId: string | null;
  durationMs: number | null;
  rootNodeId: string | null;
  nodes: ThoughtTreeNode[];
  edges: ThoughtTreeEdge[];
  tree: AtlasTraceThoughtTree | null;
  commits: SggsCommit[];
  warnings: SggsWarningCommit[];
  errors: SggsErrorCommit[];
  streamErrors: string[];
  lastCommit: SggsCommit | null;
  updatedAt: string | null;
}

export interface UseSggsLiveTreeOptions
  extends Omit<UseSggsStreamOptions, 'onCommit' | 'onError'> {
  onCommit?: (commit: SggsCommit, state: SggsLiveTreeState) => void;
  onError?: (message: string, state: SggsLiveTreeState) => void;
}

export interface UseSggsLiveTreeReturn extends UseSggsStreamReturn {
  state: SggsLiveTreeState;
  tree: AtlasTraceThoughtTree | null;
  reset: () => void;
}

// ── EventSource-like interface (for the test mock) ──────────────────────

/** Minimal EventSource shape the hook depends on. Lets the test inject
 * a queue-backed mock without polyfilling all of EventSource. */
export interface EventSourceLike {
  readonly readyState: number;
  addEventListener(
    type: string,
    listener: (ev: { data: string; lastEventId?: string }) => void,
  ): void;
  removeEventListener?(
    type: string,
    listener: (ev: { data: string; lastEventId?: string }) => void,
  ): void;
  close(): void;
  /** Optional — only present on real EventSource. */
  onopen?: ((this: EventSourceLike, ev: Event) => unknown) | null;
  /** Optional — only present on real EventSource. */
  onerror?: ((this: EventSourceLike, ev: Event) => unknown) | null;
  /** Optional — used by fetch-backed streams that complete normally. */
  onclose?: ((this: EventSourceLike) => unknown) | null;
}

// EventSource readyState constants. Hard-coded so the file does not
// need an import from `lib.dom.d.ts` types at runtime.
export const EVENT_SOURCE_CONNECTING = 0 as const;
export const EVENT_SOURCE_OPEN = 1 as const;
export const EVENT_SOURCE_CLOSED = 2 as const;

export interface FetchEventSourceOptions {
  headers?: Record<string, string>;
  fetchImpl?: typeof fetch;
}

interface ParsedSseBlock {
  type: string;
  data: string;
  lastEventId?: string;
}

function takeSseBlock(buffer: string): [string | null, string] {
  const lfIndex = buffer.indexOf('\n\n');
  const crlfIndex = buffer.indexOf('\r\n\r\n');
  if (lfIndex === -1 && crlfIndex === -1) return [null, buffer];
  if (crlfIndex !== -1 && (lfIndex === -1 || crlfIndex < lfIndex)) {
    return [buffer.slice(0, crlfIndex), buffer.slice(crlfIndex + 4)];
  }
  return [buffer.slice(0, lfIndex), buffer.slice(lfIndex + 2)];
}

function parseSseBlock(raw: string): ParsedSseBlock | null {
  let type = 'message';
  let lastEventId: string | undefined;
  const dataLines: string[] = [];

  for (const line of raw.split(/\r?\n/)) {
    if (!line || line.startsWith(':')) continue;
    const separator = line.indexOf(':');
    const field = separator === -1 ? line : line.slice(0, separator);
    const rawValue = separator === -1 ? '' : line.slice(separator + 1);
    const value = rawValue.startsWith(' ') ? rawValue.slice(1) : rawValue;

    if (field === 'event') type = value || 'message';
    if (field === 'id') lastEventId = value;
    if (field === 'data') dataLines.push(value);
  }

  if (dataLines.length === 0) return null;
  return { type, data: dataLines.join('\n'), lastEventId };
}

class FetchEventSource implements EventSourceLike {
  readonly url: string;
  readyState: number = EVENT_SOURCE_CONNECTING;
  onopen: ((this: EventSourceLike, ev: Event) => unknown) | null = null;
  onerror: ((this: EventSourceLike, ev: Event) => unknown) | null = null;
  onclose: ((this: EventSourceLike) => unknown) | null = null;

  private readonly abortController = new AbortController();
  private readonly fetchImpl: typeof fetch;
  private readonly headers: Record<string, string>;
  private readonly listeners = new Map<string, Array<(ev: { data: string; lastEventId?: string }) => void>>();
  private closed = false;

  constructor(url: string, options: FetchEventSourceOptions = {}) {
    this.url = url;
    this.fetchImpl = options.fetchImpl ?? fetch;
    this.headers = options.headers ?? {};
    void this.connect();
  }

  addEventListener(
    type: string,
    listener: (ev: { data: string; lastEventId?: string }) => void,
  ): void {
    const listeners = this.listeners.get(type) ?? [];
    listeners.push(listener);
    this.listeners.set(type, listeners);
  }

  removeEventListener(
    type: string,
    listener: (ev: { data: string; lastEventId?: string }) => void,
  ): void {
    const listeners = this.listeners.get(type) ?? [];
    this.listeners.set(
      type,
      listeners.filter((candidate) => candidate !== listener),
    );
  }

  close(): void {
    if (this.closed) return;
    this.closed = true;
    this.readyState = EVENT_SOURCE_CLOSED;
    this.abortController.abort();
  }

  private dispatch(type: string, ev: { data: string; lastEventId?: string }): void {
    for (const listener of this.listeners.get(type) ?? []) {
      listener(ev);
    }
  }

  private async connect(): Promise<void> {
    try {
      const response = await this.fetchImpl(this.url, {
        method: 'GET',
        headers: {
          Accept: 'text/event-stream',
          ...this.headers,
        },
        credentials: 'same-origin',
        signal: this.abortController.signal,
      });

      if (!response.ok || !response.body) {
        throw new Error(`Mode 7 stream failed with HTTP ${response.status}.`);
      }

      this.readyState = EVENT_SOURCE_OPEN;
      this.onopen?.call(this, new Event('open'));

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (!this.closed) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        while (true) {
          const [block, rest] = takeSseBlock(buffer);
          if (block === null) break;
          buffer = rest;
          const parsed = parseSseBlock(block);
          if (parsed) {
            this.dispatch(parsed.type, {
              data: parsed.data,
              lastEventId: parsed.lastEventId,
            });
          }
        }
      }

      if (buffer.trim()) {
        const parsed = parseSseBlock(buffer);
        if (parsed) {
          this.dispatch(parsed.type, {
            data: parsed.data,
            lastEventId: parsed.lastEventId,
          });
        }
      }

      if (!this.closed) {
        this.readyState = EVENT_SOURCE_CLOSED;
        this.onclose?.call(this);
      }
    } catch {
      if (this.closed) return;
      this.readyState = EVENT_SOURCE_CLOSED;
      this.onerror?.call(this, new Event('error'));
    }
  }
}

export function createFetchEventSource(
  url: string,
  options: FetchEventSourceOptions = {},
): EventSourceLike {
  return new FetchEventSource(url, options);
}

// ── Parsing helpers ──────────────────────────────────────────────────────

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function isSggsEventKind(value: unknown): value is SggsEventKind {
  return (
    typeof value === 'string' &&
    (SGGS_EVENT_KINDS as readonly string[]).includes(value)
  );
}

// -- Mode 7 mechanistic axis_attr selectors --------------------------------

export const MODE7_TRACE_SCHEMA_VERSION = 'mode_7_trace.v1' as const;
export type Mode7TraceSchemaVersion = typeof MODE7_TRACE_SCHEMA_VERSION;

export const MODE7_LOAD_BEARING_SLOT_TYPES = [
  'OMEGA',
  'STAGE_VAR',
  'COEFFICIENT',
  'REGISTER_LETTER',
  'DOMAIN_LETTER',
  'DRIVE_LETTER',
  'FRACTAL_K_LITERAL',
  'NOETIC_PHRASE',
] as const;
export type Mode7LoadBearingSlotType =
  (typeof MODE7_LOAD_BEARING_SLOT_TYPES)[number];

export interface Mode7ActivationLayer {
  name: string;
  l2Norm: number | null;
  meanAbs: number | null;
  maxAbs: number | null;
  hookFired: boolean | null;
  source: string;
}

export interface Mode7AttentionHead {
  label: string;
  layer: string | null;
  headIndex: number | null;
  entropy: number | null;
  weight: number | null;
  sourceToken: string | null;
  targetToken: string | null;
}

export interface Mode7LoadBearingToken {
  position: number;
  tokenId: number | null;
  token: string;
  slotType: string | null;
  slotConfidence: number | null;
  copySourceIndex: number | null;
  sourceToken: string | null;
  copyEntropy: number | null;
  phraseBiasActive: boolean | null;
  importance: number | null;
}

export interface Mode7TokenProbability {
  position: number | null;
  tokenId: number | null;
  token: string | null;
  probability: number;
  rank: number;
}

export interface Mode7CopyProbability {
  position: number | null;
  sourcePosition: number | null;
  sourceToken: string | null;
  probability: number;
  rank: number;
}

export interface Mode7LogitsCopySummary {
  positions: number;
  copiedPositions: number;
  maxLmProbability: number | null;
  maxCopyProbability: number | null;
  meanCopyEntropy: number | null;
  topLm: Mode7TokenProbability[];
  topCopy: Mode7CopyProbability[];
  routeCounts: Record<string, number>;
}

export interface Mode7StructuralCommitLinkage {
  turnId: string;
  headIndex: number;
  headName: string;
  nodeId: string;
  parentNodeId: string | null;
  nodeKind: string;
  nodeLabel: string;
  traceId: string | null;
  objectId: string | null;
  parentIds: string[];
  source: string | null;
  modelCheckpointId: string | null;
  modelCodeVersion: string | null;
  schemaVersion: string | null;
}

export interface Mode7MechanisticTrace {
  label: string;
  explanation: string;
  activationLayers: Mode7ActivationLayer[];
  attentionHeads: Mode7AttentionHead[];
  loadBearingTokens: Mode7LoadBearingToken[];
  logitsCopySummary: Mode7LogitsCopySummary;
  structuralCommit: Mode7StructuralCommitLinkage;
  warnings: string[];
  rawAxisAttrs: Record<string, unknown>;
}

function firstPlainObject(...values: unknown[]): Record<string, unknown> | null {
  for (const value of values) {
    if (isPlainObject(value)) return value;
  }
  return null;
}

function childObject(
  obj: Record<string, unknown>,
  key: string,
): Record<string, unknown> | null {
  const value = obj[key];
  return isPlainObject(value) ? value : null;
}

function stringOrNull(value: unknown): string | null {
  if (typeof value !== 'string') return null;
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function firstString(...values: unknown[]): string | null {
  for (const value of values) {
    const parsed = stringOrNull(value);
    if (parsed !== null) return parsed;
  }
  return null;
}

function numberOrNull(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function firstNumber(...values: unknown[]): number | null {
  for (const value of values) {
    const parsed = numberOrNull(value);
    if (parsed !== null) return parsed;
  }
  return null;
}

function booleanOrNull(value: unknown): boolean | null {
  return typeof value === 'boolean' ? value : null;
}

function firstBoolean(...values: unknown[]): boolean | null {
  for (const value of values) {
    const parsed = booleanOrNull(value);
    if (parsed !== null) return parsed;
  }
  return null;
}

function recordArray(value: unknown): Record<string, unknown>[] {
  if (!Array.isArray(value)) return [];
  return value.filter((item): item is Record<string, unknown> =>
    isPlainObject(item),
  );
}

function numberArray(value: unknown): number[] {
  if (!Array.isArray(value)) return [];
  return value.filter(
    (item): item is number =>
      typeof item === 'number' && Number.isFinite(item),
  );
}

function stringArray(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value
    .map((item) => stringOrNull(item))
    .filter((item): item is string => item !== null);
}

function numericRecord(value: unknown): Record<string, number> {
  if (!isPlainObject(value)) return {};
  const out: Record<string, number> = {};
  for (const [key, raw] of Object.entries(value)) {
    const parsed = numberOrNull(raw);
    if (parsed !== null) out[key] = parsed;
  }
  return out;
}

function dedupeStrings(values: string[]): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const value of values) {
    if (seen.has(value)) continue;
    seen.add(value);
    out.push(value);
  }
  return out;
}

function mode7AxisPayload(
  axisAttrs: Record<string, unknown>,
): Record<string, unknown> {
  return (
    firstPlainObject(
      axisAttrs.mode_7_trace,
      axisAttrs.mode7_trace,
      axisAttrs.mode7,
      axisAttrs.mechanistic_trace,
      axisAttrs.mechanistic,
      axisAttrs.network_attribution,
      axisAttrs.live_trace,
    ) ?? axisAttrs
  );
}

export function selectMode7AxisPayload(
  axisAttrs: Record<string, unknown>,
): Record<string, unknown> {
  return mode7AxisPayload(axisAttrs);
}

export function hasMode7MechanisticAxisAttrs(
  axisAttrs: Record<string, unknown>,
): boolean {
  if (
    firstPlainObject(
      axisAttrs.mode_7_trace,
      axisAttrs.mode7_trace,
      axisAttrs.mode7,
      axisAttrs.mechanistic_trace,
      axisAttrs.mechanistic,
      axisAttrs.network_attribution,
      axisAttrs.live_trace,
    ) !== null
  ) {
    return true;
  }

  const schema = stringOrNull(axisAttrs.schema_version);
  if (
    schema === MODE7_TRACE_SCHEMA_VERSION ||
    schema === 'mechanistic_trace.v1' ||
    schema === 'live_trace.v1'
  ) {
    return true;
  }

  return [
    'activation_layers',
    'layer_activations',
    'attention_heads',
    'decoder_per_position',
    'logits_copy_summary',
    'hook_status',
    'bottleneck_top_k',
    'p_copy_top5_per_position',
    'lm_logits_top5_per_position',
  ].some((key) => key in axisAttrs);
}

function collectHookStatus(
  payload: Record<string, unknown>,
): Record<string, boolean> {
  const out: Record<string, boolean> = {};
  const metadata = childObject(payload, 'metadata');
  const encoder = childObject(payload, 'encoder');
  const decoder = childObject(payload, 'decoder');
  const candidates = [
    payload.hook_status,
    payload.hooks,
    payload.activation_hooks,
    metadata?.hook_status,
    encoder?.hook_status,
    decoder?.hook_status,
  ];

  for (const candidate of candidates) {
    if (isPlainObject(candidate)) {
      for (const [key, raw] of Object.entries(candidate)) {
        const value = booleanOrNull(raw);
        if (value !== null) out[key] = value;
      }
    }
    for (const item of recordArray(candidate)) {
      const name = firstString(item.name, item.hook, item.layer);
      const fired = firstBoolean(item.fired, item.hook_fired, item.captured);
      if (name !== null && fired !== null) out[name] = fired;
    }
  }

  return out;
}

function pushUniqueLayer(
  layers: Mode7ActivationLayer[],
  layer: Mode7ActivationLayer,
): void {
  const existing = layers.findIndex((candidate) => candidate.name === layer.name);
  if (existing === -1) {
    layers.push(layer);
    return;
  }
  layers[existing] = {
    ...layers[existing],
    ...layer,
    l2Norm: layer.l2Norm ?? layers[existing].l2Norm,
    meanAbs: layer.meanAbs ?? layers[existing].meanAbs,
    maxAbs: layer.maxAbs ?? layers[existing].maxAbs,
    hookFired: layer.hookFired ?? layers[existing].hookFired,
  };
}

function layerHookStatus(
  hookStatus: Record<string, boolean>,
  name: string,
): boolean | null {
  if (name in hookStatus) return hookStatus[name];
  if (name.startsWith('encoder.') && '_EncoderBlock' in hookStatus) {
    return hookStatus._EncoderBlock;
  }
  if (name.startsWith('decoder.') && '_DecoderBlock' in hookStatus) {
    return hookStatus._DecoderBlock;
  }
  return null;
}

export function selectMode7ActivationLayers(
  axisAttrs: Record<string, unknown>,
): Mode7ActivationLayer[] {
  const payload = mode7AxisPayload(axisAttrs);
  const hookStatus = collectHookStatus(payload);
  const layers: Mode7ActivationLayer[] = [];

  const explicitLayers = [
    ...recordArray(payload.activation_layers),
    ...recordArray(payload.layer_activations),
  ];
  explicitLayers.forEach((item, index) => {
    const name = firstString(item.name, item.layer, item.hook) ?? `layer.${index}`;
    pushUniqueLayer(layers, {
      name,
      l2Norm: firstNumber(item.l2_norm, item.l2Norm, item.l2),
      meanAbs: firstNumber(item.mean_abs, item.meanAbs),
      maxAbs: firstNumber(item.max_abs, item.maxAbs),
      hookFired:
        firstBoolean(item.hook_fired, item.hookFired, item.fired, item.captured) ??
        layerHookStatus(hookStatus, name),
      source: 'activation_layers',
    });
  });

  const encoder = childObject(payload, 'encoder') ?? payload;
  const encoderLayerL2 = [
    ...numberArray(encoder.encoder_layer_l2),
    ...numberArray(encoder.encoder_l2_per_layer),
  ];
  encoderLayerL2.forEach((l2Norm, index) => {
    const name = `encoder.${index}`;
    pushUniqueLayer(layers, {
      name,
      l2Norm,
      meanAbs: null,
      maxAbs: null,
      hookFired: layerHookStatus(hookStatus, name),
      source: 'encoder_layer_l2',
    });
  });

  const decoderLayerL2 = [
    ...numberArray(payload.decoder_layer_l2),
    ...numberArray(payload.decoder_l2_per_layer),
  ];
  decoderLayerL2.forEach((l2Norm, index) => {
    const name = `decoder.${index}`;
    pushUniqueLayer(layers, {
      name,
      l2Norm,
      meanAbs: null,
      maxAbs: null,
      hookFired: layerHookStatus(hookStatus, name),
      source: 'decoder_layer_l2',
    });
  });

  const perLayerValues: number[][] = [];
  for (const position of decoderPositionRecords(payload)) {
    numberArray(position.layer_l2).forEach((value, index) => {
      const values = perLayerValues[index] ?? [];
      values.push(value);
      perLayerValues[index] = values;
    });
  }
  perLayerValues.forEach((values, index) => {
    const name = `decoder.${index}`;
    const l2Norm =
      values.length > 0
        ? values.reduce((sum, value) => sum + value, 0) / values.length
        : null;
    pushUniqueLayer(layers, {
      name,
      l2Norm,
      meanAbs: null,
      maxAbs: null,
      hookFired: layerHookStatus(hookStatus, name),
      source: 'decoder_per_position.layer_l2',
    });
  });

  for (const [name, fired] of Object.entries(hookStatus)) {
    pushUniqueLayer(layers, {
      name,
      l2Norm: null,
      meanAbs: null,
      maxAbs: null,
      hookFired: fired,
      source: 'hook_status',
    });
  }

  return layers;
}

export function selectMode7AttentionHeads(
  axisAttrs: Record<string, unknown>,
): Mode7AttentionHead[] {
  const payload = mode7AxisPayload(axisAttrs);
  const attention = childObject(payload, 'attention') ?? payload;
  const heads: Mode7AttentionHead[] = [];

  const explicitHeads = [
    ...recordArray(payload.attention_heads),
    ...recordArray(attention.heads),
  ];
  explicitHeads.forEach((item, index) => {
    const layer = firstString(item.layer, item.layer_name, item.module);
    const headIndex = firstNumber(item.head_index, item.headIndex, item.head);
    const label =
      firstString(item.label, item.name) ??
      `${layer ?? 'attention'}${headIndex !== null ? `.head${headIndex}` : `.${index}`}`;
    heads.push({
      label,
      layer,
      headIndex,
      entropy: firstNumber(item.entropy, item.attention_entropy),
      weight: firstNumber(item.weight, item.probability, item.score),
      sourceToken: firstString(item.source_token, item.sourceToken),
      targetToken: firstString(item.target_token, item.targetToken),
    });
  });

  const entropyPerLayer = [
    ...numberArray(payload.attention_entropy_per_layer),
    ...numberArray(attention.attention_entropy_per_layer),
  ];
  entropyPerLayer.forEach((entropy, index) => {
    heads.push({
      label: `attention.layer${index}`,
      layer: `layer.${index}`,
      headIndex: null,
      entropy,
      weight: null,
      sourceToken: null,
      targetToken: null,
    });
  });

  const entropySummary = firstPlainObject(
    payload.attention_entropy_summary,
    attention.attention_entropy_summary,
  );
  if (entropySummary) {
    const entropy = firstNumber(entropySummary.entropy, entropySummary.mean);
    if (entropy !== null) {
      heads.push({
        label: 'attention.summary',
        layer: null,
        headIndex: null,
        entropy,
        weight: null,
        sourceToken: null,
        targetToken: null,
      });
    }
  }

  return heads;
}

function sourceTokenMap(payload: Record<string, unknown>): Map<number, string> {
  const input = childObject(payload, 'input');
  const sourceTokens = [
    ...recordArray(input?.bpe_tokens),
    ...recordArray(input?.source_tokens),
    ...recordArray(payload.bpe_tokens),
    ...recordArray(payload.source_tokens),
  ];
  const map = new Map<number, string>();
  sourceTokens.forEach((item, index) => {
    const pos = firstNumber(item.position, item.index) ?? index;
    const token = firstString(item.token_str, item.token, item.text);
    if (token !== null) map.set(pos, token);
  });
  return map;
}

function decoderPositionRecords(
  payload: Record<string, unknown>,
): Record<string, unknown>[] {
  const direct = recordArray(payload.decoder_per_position);
  if (direct.length > 0) return direct;

  const lmRows = Array.isArray(payload.lm_logits_top5_per_position)
    ? payload.lm_logits_top5_per_position
    : [];
  const copyRows = Array.isArray(payload.p_copy_top5_per_position)
    ? payload.p_copy_top5_per_position
    : [];
  const slotTypes = Array.isArray(payload.slot_type_decision_per_position)
    ? payload.slot_type_decision_per_position
    : [];
  const slotConfidences = Array.isArray(
    payload.slot_type_confidence_per_position,
  )
    ? payload.slot_type_confidence_per_position
    : [];
  const copySources = Array.isArray(payload.copy_source_indices)
    ? payload.copy_source_indices
    : [];
  const copyEntropies = Array.isArray(payload.p_copy_entropy_per_position)
    ? payload.p_copy_entropy_per_position
    : [];
  const decodedTokens = Array.isArray(payload.raw_decoded_tokens)
    ? payload.raw_decoded_tokens
    : [];

  const count = Math.max(
    lmRows.length,
    copyRows.length,
    slotTypes.length,
    slotConfidences.length,
    copySources.length,
    copyEntropies.length,
    decodedTokens.length,
  );
  return Array.from({ length: count }, (_, position) => ({
    position,
    lm_logits_top5: lmRows[position],
    p_copy_top5: copyRows[position],
    slot_type: slotTypes[position],
    slot_type_confidence: slotConfidences[position],
    copy_source_index: copySources[position],
    p_copy_entropy: copyEntropies[position],
    decoded_token_id: decodedTokens[position],
  }));
}

function topLmFromEntry(
  entry: unknown,
  position: number | null,
  rank: number,
): Mode7TokenProbability | null {
  if (Array.isArray(entry)) {
    const tokenId = numberOrNull(entry[0]);
    const token = typeof entry[0] === 'string' ? entry[0] : stringOrNull(entry[2]);
    const probability = firstNumber(entry[1], entry[2]);
    if (probability === null) return null;
    return { position, tokenId, token, probability, rank };
  }
  if (!isPlainObject(entry)) return null;
  const probability = firstNumber(entry.probability, entry.prob, entry.p, entry.score);
  if (probability === null) return null;
  return {
    position,
    tokenId: firstNumber(entry.token_id, entry.tokenId, entry.id),
    token: firstString(entry.token_str, entry.token, entry.text),
    probability,
    rank,
  };
}

function topCopyFromEntry(
  entry: unknown,
  position: number | null,
  rank: number,
  sources: Map<number, string>,
): Mode7CopyProbability | null {
  if (Array.isArray(entry)) {
    const sourcePosition = numberOrNull(entry[0]);
    const probability = firstNumber(entry[1], entry[2]);
    if (probability === null) return null;
    return {
      position,
      sourcePosition,
      sourceToken:
        sourcePosition !== null ? sources.get(sourcePosition) ?? null : null,
      probability,
      rank,
    };
  }
  if (!isPlainObject(entry)) return null;
  const probability = firstNumber(entry.probability, entry.prob, entry.p, entry.score);
  if (probability === null) return null;
  const sourcePosition = firstNumber(
    entry.source_position,
    entry.sourcePosition,
    entry.src_position,
    entry.srcPosition,
    entry.position,
  );
  return {
    position,
    sourcePosition,
    sourceToken:
      firstString(entry.source_token, entry.sourceToken, entry.token) ??
      (sourcePosition !== null ? sources.get(sourcePosition) ?? null : null),
    probability,
    rank,
  };
}

function topLmForPosition(
  position: Record<string, unknown>,
  outputPosition: number | null,
): Mode7TokenProbability[] {
  return (Array.isArray(position.lm_logits_top5)
    ? position.lm_logits_top5
    : Array.isArray(position.lm_top5)
      ? position.lm_top5
      : []
  )
    .map((entry, index) => topLmFromEntry(entry, outputPosition, index + 1))
    .filter((entry): entry is Mode7TokenProbability => entry !== null);
}

function topCopyForPosition(
  position: Record<string, unknown>,
  outputPosition: number | null,
  sources: Map<number, string>,
): Mode7CopyProbability[] {
  return (Array.isArray(position.p_copy_top5)
    ? position.p_copy_top5
    : Array.isArray(position.copy_top5)
      ? position.copy_top5
      : []
  )
    .map((entry, index) =>
      topCopyFromEntry(entry, outputPosition, index + 1, sources),
    )
    .filter((entry): entry is Mode7CopyProbability => entry !== null);
}

function isLoadBearingSlot(slotType: string | null): boolean {
  return (
    slotType !== null &&
    (MODE7_LOAD_BEARING_SLOT_TYPES as readonly string[]).includes(slotType)
  );
}

export function selectMode7LoadBearingTokens(
  axisAttrs: Record<string, unknown>,
): Mode7LoadBearingToken[] {
  const payload = mode7AxisPayload(axisAttrs);
  const sources = sourceTokenMap(payload);
  const explicit = [
    ...recordArray(payload.load_bearing_tokens),
    ...recordArray(payload.loadBearingTokens),
  ];
  if (explicit.length > 0) {
    return explicit.map((item, index) => {
      const copySourceIndex = firstNumber(
        item.copy_source_index,
        item.copySourceIndex,
        item.source_position,
      );
      return {
        position: firstNumber(item.position, item.index) ?? index,
        tokenId: firstNumber(item.token_id, item.tokenId, item.id),
        token: firstString(item.token_str, item.token, item.text) ?? '',
        slotType: firstString(item.slot_type, item.slotType),
        slotConfidence: firstNumber(
          item.slot_type_confidence,
          item.slotConfidence,
          item.confidence,
        ),
        copySourceIndex,
        sourceToken:
          firstString(item.source_token, item.sourceToken) ??
          (copySourceIndex !== null ? sources.get(copySourceIndex) ?? null : null),
        copyEntropy: firstNumber(item.p_copy_entropy, item.copyEntropy),
        phraseBiasActive: booleanOrNull(item.phrase_bias_active),
        importance: firstNumber(item.importance, item.weight, item.probability),
      };
    });
  }

  return decoderPositionRecords(payload)
    .map((position, index): Mode7LoadBearingToken | null => {
      const outputPosition = firstNumber(position.position, position.index) ?? index;
      const slotType = firstString(position.slot_type, position.slotType);
      const copySourceIndex = firstNumber(
        position.copy_source_index,
        position.copySourceIndex,
      );
      const copyIsActive = copySourceIndex !== null && copySourceIndex >= 0;
      const phraseBiasActive = booleanOrNull(position.phrase_bias_active);
      const topCopy = topCopyForPosition(position, outputPosition, sources);
      const maxCopy = topCopy[0]?.probability ?? null;
      if (
        !isLoadBearingSlot(slotType) &&
        !copyIsActive &&
        phraseBiasActive !== true
      ) {
        return null;
      }
      return {
        position: outputPosition,
        tokenId: firstNumber(position.decoded_token_id, position.token_id),
        token:
          firstString(
            position.decoded_token_str,
            position.token_str,
            position.token,
          ) ?? '',
        slotType,
        slotConfidence: firstNumber(
          position.slot_type_confidence,
          position.slotConfidence,
        ),
        copySourceIndex,
        sourceToken:
          copyIsActive
            ? sources.get(copySourceIndex) ?? null
            : topCopy[0]?.sourceToken ?? null,
        copyEntropy: firstNumber(position.p_copy_entropy, position.copyEntropy),
        phraseBiasActive,
        importance: Math.max(
          firstNumber(
            position.slot_type_confidence,
            position.slotConfidence,
            0,
          ) ?? 0,
          maxCopy ?? 0,
        ),
      };
    })
    .filter((item): item is Mode7LoadBearingToken => item !== null);
}

export function selectMode7LogitsCopySummary(
  axisAttrs: Record<string, unknown>,
): Mode7LogitsCopySummary {
  const payload = mode7AxisPayload(axisAttrs);
  const explicit = firstPlainObject(
    payload.logits_copy_summary,
    payload.logitsCopySummary,
  );
  const sources = sourceTokenMap(payload);
  const positions = decoderPositionRecords(payload);
  const topLm = positions.flatMap((position, index) =>
    topLmForPosition(
      position,
      firstNumber(position.position, position.index) ?? index,
    ),
  );
  const topCopy = positions.flatMap((position, index) =>
    topCopyForPosition(
      position,
      firstNumber(position.position, position.index) ?? index,
      sources,
    ),
  );
  const copyEntropies = positions
    .map((position) => firstNumber(position.p_copy_entropy, position.copyEntropy))
    .filter((value): value is number => value !== null);
  const copiedPositions = positions.filter((position) => {
    const copySource = firstNumber(
      position.copy_source_index,
      position.copySourceIndex,
    );
    return copySource !== null && copySource >= 0;
  }).length;

  const sortedLm = topLm
    .slice()
    .sort((a, b) => b.probability - a.probability)
    .slice(0, 5);
  const sortedCopy = topCopy
    .slice()
    .sort((a, b) => b.probability - a.probability)
    .slice(0, 5);

  return {
    positions:
      firstNumber(explicit?.positions, explicit?.position_count) ??
      positions.length,
    copiedPositions:
      firstNumber(explicit?.copied_positions, explicit?.copiedPositions) ??
      copiedPositions,
    maxLmProbability:
      firstNumber(explicit?.max_lm_probability, explicit?.maxLmProbability) ??
      sortedLm[0]?.probability ??
      null,
    maxCopyProbability:
      firstNumber(
        explicit?.max_copy_probability,
        explicit?.maxCopyProbability,
      ) ??
      sortedCopy[0]?.probability ??
      null,
    meanCopyEntropy:
      firstNumber(explicit?.mean_copy_entropy, explicit?.meanCopyEntropy) ??
      (copyEntropies.length > 0
        ? copyEntropies.reduce((sum, value) => sum + value, 0) /
          copyEntropies.length
        : null),
    topLm: sortedLm,
    topCopy: sortedCopy,
    routeCounts: {
      ...numericRecord(payload.emission_route_counts),
      ...numericRecord(payload.route_counts),
      ...numericRecord(explicit?.route_counts),
      ...numericRecord(explicit?.routeCounts),
    },
  };
}

export function selectMode7StructuralCommitLinkage(
  commit: SggsHeadCommit,
): Mode7StructuralCommitLinkage {
  const payload = mode7AxisPayload(commit.axis_attrs);
  const structural =
    firstPlainObject(
      payload.structural_commit,
      payload.structural,
      payload.commit_linkage,
    ) ?? payload;
  const parentIds = dedupeStrings([
    ...stringArray(payload.parent_ids),
    ...stringArray(structural.parent_ids),
    commit.turn_id,
    ...(commit.parent_node_id ? [commit.parent_node_id] : []),
  ]);
  return {
    turnId: commit.turn_id,
    headIndex: commit.head_index,
    headName: commit.head_name,
    nodeId: commit.node_id,
    parentNodeId: commit.parent_node_id,
    nodeKind: commit.node_kind,
    nodeLabel: commit.node_label,
    traceId: firstString(
      payload.trace_id,
      structural.trace_id,
      payload.final_trace_id,
      structural.final_trace_id,
    ),
    objectId: firstString(
      payload.id,
      structural.id,
      payload.object_id,
      structural.object_id,
    ),
    parentIds,
    source: firstString(payload.source, structural.source),
    modelCheckpointId: firstString(
      payload.model_checkpoint_id,
      structural.model_checkpoint_id,
    ),
    modelCodeVersion: firstString(
      payload.model_code_version,
      structural.model_code_version,
    ),
    schemaVersion: firstString(payload.schema_version, structural.schema_version),
  };
}

export function selectMode7MechanisticLabel(commit: SggsHeadCommit): string {
  const payload = mode7AxisPayload(commit.axis_attrs);
  const summary = childObject(payload, 'summary');
  const dominant = [
    firstString(summary?.dominant_noetic_name),
    firstString(summary?.dominant_domain_name),
  ]
    .filter((part): part is string => part !== null)
    .join(' / ');
  return (
    firstString(
      payload.mechanistic_label,
      payload.label,
      summary?.label,
      dominant,
    ) ?? `Network Attribution: ${shortLiveLabel(commit.node_label, commit.head_name)}`
  );
}

export function selectMode7MechanisticExplanation(
  commit: SggsHeadCommit,
): string {
  const payload = mode7AxisPayload(commit.axis_attrs);
  const summary = childObject(payload, 'summary');
  const explicit = firstString(
    payload.mechanistic_explanation,
    payload.explanation,
    summary?.explanation,
  );
  if (explicit !== null) return explicit;

  const layerCount = selectMode7ActivationLayers(commit.axis_attrs).length;
  const tokenCount = selectMode7LoadBearingTokens(commit.axis_attrs).length;
  const copySummary = selectMode7LogitsCopySummary(commit.axis_attrs);
  return (
    `Activation hooks: ${layerCount}; load-bearing tokens: ${tokenCount}; ` +
    `copy-linked positions: ${copySummary.copiedPositions}/${copySummary.positions}.`
  );
}

export function selectMode7MechanisticTrace(
  commit: SggsHeadCommit,
): Mode7MechanisticTrace | null {
  if (!hasMode7MechanisticAxisAttrs(commit.axis_attrs)) return null;
  const payload = mode7AxisPayload(commit.axis_attrs);
  const summary = childObject(payload, 'summary');
  return {
    label: selectMode7MechanisticLabel(commit),
    explanation: selectMode7MechanisticExplanation(commit),
    activationLayers: selectMode7ActivationLayers(commit.axis_attrs),
    attentionHeads: selectMode7AttentionHeads(commit.axis_attrs),
    loadBearingTokens: selectMode7LoadBearingTokens(commit.axis_attrs),
    logitsCopySummary: selectMode7LogitsCopySummary(commit.axis_attrs),
    structuralCommit: selectMode7StructuralCommitLinkage(commit),
    warnings: dedupeStrings([
      ...stringArray(payload.trace_warnings),
      ...stringArray(summary?.trace_warnings),
      ...stringArray(payload.diagnostics),
    ]),
    rawAxisAttrs: commit.axis_attrs,
  };
}

// ── Per-kind field validators ────────────────────────────────────────────
//
// Codex audit 3f495ba blocker 2 (2026-05-13): the previous parser accepted
// any object whose `kind` was in the known set and whose `turn_id` was a
// string. That meant a malformed `head_commit` missing `node_id` /
// `node_label` would still dispatch through `onCommit` and could corrupt
// the live graph. These validators enforce every field declared by the
// discriminated-union interfaces above + the schema_version.

const REQ_STR_FIELDS: Record<SggsEventKind, readonly string[]> = {
  turn_start: ['user_text', 'created_at'],
  head_commit: ['head_name', 'node_id', 'node_kind', 'node_label'],
  edge_commit: ['edge_id', 'source_node_id', 'target_node_id', 'edge_kind'],
  turn_end: ['final_trace_id', 'ended_at'],
  warning: ['severity', 'message'],
  error: ['code', 'message'],
};

const REQ_NUM_FIELDS: Record<SggsEventKind, readonly string[]> = {
  turn_start: [],
  head_commit: ['head_index'],
  edge_commit: [],
  turn_end: ['total_heads', 'duration_ms'],
  warning: [],
  error: [],
};

function validateCommitFields(
  kind: SggsEventKind,
  payload: Record<string, unknown>,
): string | null {
  if (payload.schema_version !== SGGS_STREAM_SCHEMA_VERSION) {
    return (
      `schema_version expected "${SGGS_STREAM_SCHEMA_VERSION}" ` +
      `got "${String(payload.schema_version)}"`
    );
  }
  for (const field of REQ_STR_FIELDS[kind]) {
    if (typeof payload[field] !== 'string') {
      return `${kind} missing string field "${field}"`;
    }
  }
  for (const field of REQ_NUM_FIELDS[kind]) {
    if (typeof payload[field] !== 'number') {
      return `${kind} missing numeric field "${field}"`;
    }
  }
  if (kind === 'head_commit') {
    // parent_node_id may be string OR null per the type union
    const parent = payload.parent_node_id;
    if (parent !== null && typeof parent !== 'string') {
      return 'head_commit.parent_node_id must be string or null';
    }
    if (!isPlainObject(payload.axis_attrs)) {
      return 'head_commit.axis_attrs must be an object';
    }
  }
  return null;
}

/**
 * Parse a `data:` line payload into a typed `SggsCommit`.
 *
 * Returns `{ ok: true, commit }` on success or `{ ok: false, error }`
 * naming the first failure. Used by the hook AND directly importable
 * for offline trace replay (e.g. piping a recorded SSE log through
 * this parser to reconstruct the commit sequence).
 */
export function parseSggsCommit(
  expectedKind: string,
  rawData: string,
): { ok: true; commit: SggsCommit } | { ok: false; error: string } {
  let parsed: unknown;
  try {
    parsed = JSON.parse(rawData);
  } catch (err) {
    const msg = err instanceof Error ? err.message : 'Unknown JSON parse error.';
    return { ok: false, error: `Could not parse SSE data JSON: ${msg}` };
  }
  if (!isPlainObject(parsed)) {
    return { ok: false, error: 'SSE data was not a JSON object.' };
  }
  const kind = parsed.kind;
  if (!isSggsEventKind(kind)) {
    return {
      ok: false,
      error: `Unknown SGGS event kind: ${String(kind)}`,
    };
  }
  // The event name on the SSE channel and the `kind` field inside the
  // JSON payload should agree. A mismatch suggests the producer wired
  // the wrong helper to the wrong channel — surface it.
  if (expectedKind && kind !== expectedKind) {
    return {
      ok: false,
      error: `SSE event name "${expectedKind}" disagrees with payload kind "${kind}"`,
    };
  }
  if (typeof parsed.turn_id !== 'string') {
    return { ok: false, error: 'commit is missing turn_id.' };
  }
  // Per-kind structural validation (Codex audit 3f495ba blocker 2).
  const fieldError = validateCommitFields(kind, parsed);
  if (fieldError !== null) {
    return { ok: false, error: fieldError };
  }
  // The cast is checked structurally above; downstream consumers
  // discriminate on `kind`.
  return { ok: true, commit: parsed as unknown as SggsCommit };
}

// -- Live tree state accumulation ------------------------------------------

function nowIso(): string {
  return new Date().toISOString();
}

function normalizeNodeLabel(label: string, axisAttrs: Record<string, unknown>): string {
  const normalized = axisAttrs.normalized_label;
  if (typeof normalized === 'string' && normalized.trim()) {
    return normalized;
  }
  return label.trim().toLowerCase();
}

function shortLiveLabel(value: string, fallback: string): string {
  const trimmed = value.trim() || fallback;
  return trimmed.length > 64 ? `${trimmed.slice(0, 61)}...` : trimmed;
}

function rootNodeFromTurnStart(commit: SggsTurnStartCommit): ThoughtTreeNode {
  const label = shortLiveLabel(commit.user_text, 'Mode 7 live prompt');
  return {
    id: 'n0',
    node_key: `mode7|${commit.turn_id}|prompt`,
    kind: 'user_prompt',
    role: 'live_prompt',
    label,
    normalized_label: label.toLowerCase(),
    text: commit.user_text,
  };
}

function nodeFromHeadCommit(commit: SggsHeadCommit): ThoughtTreeNode {
  const text = commit.axis_attrs.text;
  return {
    id: commit.node_id,
    node_key: commit.node_id,
    kind: commit.node_kind,
    role: commit.head_name,
    label: commit.node_label,
    normalized_label: normalizeNodeLabel(commit.node_label, commit.axis_attrs),
    axis_attrs: commit.axis_attrs,
    ...(typeof text === 'string' ? { text } : {}),
  };
}

function edgeFromEdgeCommit(commit: SggsEdgeCommit): ThoughtTreeEdge {
  return {
    id: commit.edge_id,
    edge_key: commit.edge_id,
    source: commit.source_node_id,
    target: commit.target_node_id,
    source_key: commit.source_node_id,
    target_key: commit.target_node_id,
    kind: commit.edge_kind,
  };
}

function syntheticParentEdge(source: string, target: string): ThoughtTreeEdge {
  const id = `parent:${source}->${target}`;
  return {
    id,
    edge_key: id,
    source,
    target,
    source_key: source,
    target_key: target,
    kind: 'parent_child',
  };
}

function upsertNode(nodes: ThoughtTreeNode[], node: ThoughtTreeNode): ThoughtTreeNode[] {
  const index = nodes.findIndex((candidate) => candidate.id === node.id);
  if (index === -1) return [...nodes, node];
  const next = nodes.slice();
  next[index] = { ...next[index], ...node };
  return next;
}

function upsertEdge(edges: ThoughtTreeEdge[], edge: ThoughtTreeEdge): ThoughtTreeEdge[] {
  const explicitEdges = edge.id.startsWith('parent:')
    ? edges
    : edges.filter(
        (candidate) =>
          !(
            candidate.id.startsWith('parent:') &&
            candidate.source === edge.source &&
            candidate.target === edge.target
          ),
      );
  const index = explicitEdges.findIndex((candidate) => candidate.id === edge.id);
  if (index === -1) return [...explicitEdges, edge];
  const next = explicitEdges.slice();
  next[index] = { ...next[index], ...edge };
  return next;
}

function toRootNode(
  node: ThoughtTreeNode,
  children: ThoughtTreeRootNode[],
): ThoughtTreeRootNode {
  return {
    id: node.id,
    node_key: node.node_key,
    kind: node.kind,
    role: node.role,
    label: node.label,
    normalized_label: node.normalized_label,
    ...(node.axis_attrs ? { axis_attrs: node.axis_attrs } : {}),
    ...(node.text ? { text: node.text } : {}),
    ...(children.length > 0 ? { children } : {}),
  };
}

function chooseRootNodeId(
  nodes: ThoughtTreeNode[],
  edges: ThoughtTreeEdge[],
  preferredRootId: string | null,
): string | null {
  if (preferredRootId && nodes.some((node) => node.id === preferredRootId)) {
    return preferredRootId;
  }
  const targets = new Set(edges.map((edge) => edge.target));
  return nodes.find((node) => !targets.has(node.id))?.id ?? nodes[0]?.id ?? null;
}

function buildLiveThoughtTree(
  nodes: ThoughtTreeNode[],
  edges: ThoughtTreeEdge[],
  preferredRootId: string | null,
): AtlasTraceThoughtTree | null {
  const rootId = chooseRootNodeId(nodes, edges, preferredRootId);
  if (!rootId) return null;

  const nodesById = new Map(nodes.map((node) => [node.id, node]));
  const childrenBySource = new Map<string, ThoughtTreeEdge[]>();
  for (const edge of edges) {
    if (!nodesById.has(edge.source) || !nodesById.has(edge.target)) continue;
    const list = childrenBySource.get(edge.source) ?? [];
    list.push(edge);
    childrenBySource.set(edge.source, list);
  }

  const visit = (id: string, seen: Set<string>): ThoughtTreeRootNode | null => {
    const node = nodesById.get(id);
    if (!node || seen.has(id)) return null;
    const nextSeen = new Set(seen);
    nextSeen.add(id);
    const childEdges = childrenBySource.get(id) ?? [];
    const children = childEdges
      .map((edge) => visit(edge.target, nextSeen))
      .filter((child): child is ThoughtTreeRootNode => child !== null);
    return toRootNode(node, children);
  };

  const root = visit(rootId, new Set());
  if (!root) return null;

  return {
    root,
    nodes,
    edges,
    node_count: nodes.length,
    edge_count: edges.length,
  };
}

export function createEmptySggsLiveTreeState(): SggsLiveTreeState {
  return {
    turnId: null,
    userText: null,
    startedAt: null,
    endedAt: null,
    finalTraceId: null,
    durationMs: null,
    rootNodeId: null,
    nodes: [],
    edges: [],
    tree: null,
    commits: [],
    warnings: [],
    errors: [],
    streamErrors: [],
    lastCommit: null,
    updatedAt: null,
  };
}

function withTree(
  state: SggsLiveTreeState,
  nodes: ThoughtTreeNode[],
  edges: ThoughtTreeEdge[],
  rootNodeId = state.rootNodeId,
): Pick<SggsLiveTreeState, 'nodes' | 'edges' | 'rootNodeId' | 'tree'> {
  return {
    nodes,
    edges,
    rootNodeId,
    tree: buildLiveThoughtTree(nodes, edges, rootNodeId),
  };
}

export function applySggsCommitToLiveTree(
  state: SggsLiveTreeState,
  commit: SggsCommit,
): SggsLiveTreeState {
  const base = {
    ...state,
    commits: [...state.commits, commit],
    lastCommit: commit,
    updatedAt: nowIso(),
  };

  switch (commit.kind) {
    case SGGS_EVENT_TURN_START:
      {
        const rootNode = rootNodeFromTurnStart(commit);
        const empty = createEmptySggsLiveTreeState();
        return {
          ...empty,
          turnId: commit.turn_id,
          userText: commit.user_text,
          startedAt: commit.created_at,
          commits: [commit],
          lastCommit: commit,
          updatedAt: base.updatedAt,
          ...withTree(empty, [rootNode], [], rootNode.id),
        };
      }

    case SGGS_EVENT_HEAD_COMMIT: {
      const node = nodeFromHeadCommit(commit);
      const nodes = upsertNode(base.nodes, node);
      const rootNodeId =
        commit.parent_node_id === null && base.rootNodeId === null
          ? commit.node_id
          : base.rootNodeId;
      const parentNodeId =
        commit.parent_node_id ??
        (base.rootNodeId && commit.node_id !== base.rootNodeId ? base.rootNodeId : null);
      const edges =
        parentNodeId === null
          ? base.edges
          : upsertEdge(
              base.edges,
              syntheticParentEdge(parentNodeId, commit.node_id),
            );
      return {
        ...base,
        turnId: base.turnId ?? commit.turn_id,
        ...withTree(base, nodes, edges, rootNodeId),
      };
    }

    case SGGS_EVENT_EDGE_COMMIT: {
      const edges = upsertEdge(base.edges, edgeFromEdgeCommit(commit));
      return {
        ...base,
        turnId: base.turnId ?? commit.turn_id,
        ...withTree(base, base.nodes, edges),
      };
    }

    case SGGS_EVENT_TURN_END:
      return {
        ...base,
        turnId: base.turnId ?? commit.turn_id,
        endedAt: commit.ended_at,
        finalTraceId: commit.final_trace_id,
        durationMs: commit.duration_ms,
      };

    case SGGS_EVENT_WARNING:
      return {
        ...base,
        turnId: base.turnId ?? commit.turn_id,
        warnings: [...base.warnings, commit],
      };

    case SGGS_EVENT_ERROR:
      return {
        ...base,
        turnId: base.turnId ?? commit.turn_id,
        errors: [...base.errors, commit],
      };
  }
}

// ── Hook ─────────────────────────────────────────────────────────────────

/**
 * Subscribe to an SGGS SSE stream and dispatch parsed commits.
 *
 * Reconnect: on transient disconnect, the browser-native EventSource
 * sends `Last-Event-ID: <id>` automatically on the reconnect attempt.
 * The hook tracks the last successfully-dispatched id in component
 * state so external consumers (status panels, dev tools) can render
 * "currently at event 0a1b2c…" without subscribing twice.
 *
 * Parse-error policy: a single malformed event invokes `onError` but
 * does NOT close the stream. Transport-level errors surface via
 * `onError` too; the EventSource handles reconnect itself.
 */
export function useSggsStream(opts: UseSggsStreamOptions): UseSggsStreamReturn {
  const { url, enabled, onCommit, onError, eventSourceFactory } = opts;
  const [status, setStatus] = useState<SggsStreamStatus>('idle');
  const [lastEventId, setLastEventId] = useState<string | null>(null);

  // Stable refs for callbacks so the connection effect does not retear
  // on every parent re-render. Matches the pattern used in TraceLoader.
  const onCommitRef = useRef(onCommit);
  const onErrorRef = useRef(onError);
  useEffect(() => {
    onCommitRef.current = onCommit;
  }, [onCommit]);
  useEffect(() => {
    onErrorRef.current = onError;
  }, [onError]);

  useEffect(() => {
    if (!enabled) {
      setStatus('idle');
      return;
    }

    const factory =
      eventSourceFactory ??
      ((u: string): EventSourceLike => {
        // Defensive: in non-browser test environments without
        // EventSource, fall through to an error rather than crashing
        // at module-import time.
        if (typeof EventSource === 'undefined') {
          throw new Error(
            'EventSource is not available in this environment — pass eventSourceFactory.',
          );
        }
        return new EventSource(u) as unknown as EventSourceLike;
      });

    let source: EventSourceLike | null = null;
    try {
      setStatus('connecting');
      source = factory(url);
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setStatus('error');
      onErrorRef.current?.(`Could not open SGGS stream: ${msg}`);
      return;
    }

    const handleCommit = (kind: string) =>
      (ev: { data: string; lastEventId?: string }): void => {
        const result = parseSggsCommit(kind, ev.data);
        if (!result.ok) {
          onErrorRef.current?.(result.error);
          return;
        }
        if (ev.lastEventId) {
          setLastEventId(ev.lastEventId);
        }
        onCommitRef.current(result.commit);
      };

    // Wire one listener per known kind so the browser dispatches to
    // the right handler based on the SSE `event:` line. Also accept
    // default 'message' events and trust the embedded `kind` field.
    const listeners: Array<{
      kind: string;
      fn: (ev: { data: string; lastEventId?: string }) => void;
    }> = [];
    for (const kind of SGGS_EVENT_KINDS) {
      const fn = handleCommit(kind);
      source.addEventListener(kind, fn);
      listeners.push({ kind, fn });
    }
    const defaultMessageHandler = handleCommit('');
    source.addEventListener('message', defaultMessageHandler);
    listeners.push({ kind: 'message', fn: defaultMessageHandler });

    // Status wiring — `onopen` / `onerror` may be undefined on a mock
    // source; guard each.
    const realSource = source as EventSourceLike & {
      onopen?: ((this: EventSourceLike, ev: Event) => unknown) | null;
      onerror?: ((this: EventSourceLike, ev: Event) => unknown) | null;
    };
    if ('onopen' in realSource) {
      realSource.onopen = () => setStatus('open');
    }
    if ('onerror' in realSource) {
      realSource.onerror = () => {
        // EventSource auto-reconnects unless explicitly closed; we
        // report 'error' but expect the next 'open' to flip status
        // back. If the producer hard-closes (readyState=CLOSED) the
        // status sticks as 'closed' via the cleanup below.
        setStatus(
          realSource.readyState === EVENT_SOURCE_CLOSED ? 'closed' : 'error',
        );
        onErrorRef.current?.('SGGS stream transport error.');
      };
    }
    if ('onclose' in realSource) {
      realSource.onclose = () => setStatus('closed');
    }

    return () => {
      // Detach listeners (in environments where removeEventListener is
      // implemented; on real EventSource the close() call disposes them
      // anyway).
      if (source) {
        for (const { kind, fn } of listeners) {
          source.removeEventListener?.(kind, fn);
        }
        source.close();
        setStatus('closed');
      }
    };
    // eventSourceFactory is intentionally captured at mount-time so a
    // test does not have to memoize its mock factory; same pattern as
    // TraceLoader.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [url, enabled]);

  return { status, lastEventId };
}

/**
 * Subscribe to an SGGS stream and accumulate a UI-ready Thought Tree.
 *
 * This adapter is intentionally small: IdeaAtlasPage and CompilerPage can
 * render `tree` directly with the existing ThoughtTreeView/SggsScene once
 * they decide where to mount live Mode 7 output.
 */
export function useSggsLiveTree(
  opts: UseSggsLiveTreeOptions,
): UseSggsLiveTreeReturn {
  const { onCommit, onError, ...streamOpts } = opts;
  const [state, setState] = useState<SggsLiveTreeState>(() =>
    createEmptySggsLiveTreeState(),
  );

  const onCommitRef = useRef(onCommit);
  const onErrorRef = useRef(onError);
  useEffect(() => {
    onCommitRef.current = onCommit;
  }, [onCommit]);
  useEffect(() => {
    onErrorRef.current = onError;
  }, [onError]);

  const handleCommit = useCallback((commit: SggsCommit) => {
    setState((prev) => {
      const next = applySggsCommitToLiveTree(prev, commit);
      onCommitRef.current?.(commit, next);
      return next;
    });
  }, []);

  const handleError = useCallback((message: string) => {
    setState((prev) => {
      const next = {
        ...prev,
        streamErrors: [...prev.streamErrors, message],
        updatedAt: nowIso(),
      };
      onErrorRef.current?.(message, next);
      return next;
    });
  }, []);

  const stream = useSggsStream({
    ...streamOpts,
    onCommit: handleCommit,
    onError: handleError,
  });

  const reset = useCallback(() => {
    setState(createEmptySggsLiveTreeState());
  }, []);

  return {
    ...stream,
    state,
    tree: state.tree,
    reset,
  };
}
