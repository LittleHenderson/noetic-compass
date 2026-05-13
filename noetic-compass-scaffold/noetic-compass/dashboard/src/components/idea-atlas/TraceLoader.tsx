import { useCallback, useEffect, useRef, useState } from 'react';
import {
  type AtlasTrace,
  TRACE_SCHEMA_VERSION,
  validateAtlasTrace,
} from '../../lib/trace';

// ── Bundled demo trace ──
//
// A minimal, fully-valid traceability_v0 trace. Mirrors the shape
// `build_v0_trace` emits for the prompt "explain a thought becoming
// action" — the canonical sample we tell stakeholders to try.
//
// This is embedded (not fetched) so the demo button works offline and
// without a backend.
export const DEMO_TRACE: AtlasTrace = {
  schema_version: TRACE_SCHEMA_VERSION,
  trace_id: '00000000-0000-4000-8000-000000000000',
  created_at: '2026-05-13T17:30:00Z',
  input: {
    input_kind: 'nl_bridge',
    user_text: 'explain a thought becoming action',
    cas_expression: '^9^O',
    source_tokens: [{ index: 0, token: '^9^O' }],
    nl_bridge: {
      matched_pattern: 'thought becoming action',
      confidence: 0.95,
      rationale: 'Below/Effect in the Operational domain.',
      inferred_cas_expression: '^9^O',
    },
  },
  output: {
    english:
      'Below/Effect in the Operational domain — a thought landing as behavior.',
    n_tokens: 18,
  },
  copy: {
    copied_identifiers: [],
    missed_identifiers: [],
    coverage: null,
    per_identifier: [],
  },
  slot_trace: {
    length: 18,
    slot_counts_by_label: { 'joining word': 18, 'named identifier': 0 },
    longest_stage_var_run: 0,
    raw_trace: null,
  },
  confidence: {
    qualitative_coverage: 'strong',
    slot_quality: 'only joining words generated',
    caveats: [],
    warning_flags: [],
  },
  thought_tree: {
    root: {
      id: 'n0',
      node_key: 'user_prompt|input|explain a thought becoming action|',
      kind: 'user_prompt',
      role: 'input',
      label: 'explain a thought becoming action',
      normalized_label: 'explain a thought becoming action',
      text: 'explain a thought becoming action',
      children: [
        {
          id: 'n1',
          node_key: 'nl_bridge|pattern|thought becoming action|confidence=0.95,inferred_cas=^9^O',
          kind: 'nl_bridge',
          role: 'pattern',
          label: 'thought becoming action',
          normalized_label: 'thought becoming action',
          axis_attrs: { confidence: 0.95, inferred_cas: '^9^O' },
          text: 'Matched the English request to a compact CAS expression.',
          children: [
            {
              id: 'n2',
              node_key: 'cas_expression|inferred|^9^o|',
              kind: 'cas_expression',
              role: 'inferred',
              label: '^9^O',
              normalized_label: '^9^o',
              text: 'Below/Effect in the Operational domain — a thought landing as behavior.',
              children: [
                {
                  id: 'n3',
                  node_key: 'model_generation|output|below/effect in the operational domain — a thought landing as behavior.|',
                  kind: 'model_generation',
                  role: 'output',
                  label: 'thought landing as behavior',
                  normalized_label: 'thought landing as behavior',
                  text: 'Below/Effect in the Operational domain — a thought landing as behavior.',
                  children: [
                    {
                      id: 'n4',
                      node_key: 'slot_pattern|summary|only joining words generated|length=18,longest_stage_var_run=0,stage_var_count=0',
                      kind: 'slot_pattern',
                      role: 'summary',
                      label: 'slot trace: plain explanation',
                      normalized_label: 'slot trace: plain explanation',
                      axis_attrs: {
                        length: 18,
                        longest_stage_var_run: 0,
                        stage_var_count: 0,
                      },
                      text: 'The output is an identifier-free explanation, so every generated token stays in the plain-language slot.',
                      children: [],
                    },
                    {
                      id: 'n5',
                      node_key: 'confidence_marker|strong|coverage: strong|band=strong',
                      kind: 'confidence_marker',
                      role: 'strong',
                      label: 'coverage: strong',
                      normalized_label: 'coverage: strong',
                      axis_attrs: { band: 'strong' },
                      text: 'No source identifiers were expected here, so there is no copy warning.',
                      children: [],
                    },
                  ],
                },
              ],
            },
          ],
        },
      ],
    },
    nodes: [
      {
        id: 'n0',
        node_key: 'user_prompt|input|explain a thought becoming action|',
        kind: 'user_prompt',
        role: 'input',
        label: 'explain a thought becoming action',
        normalized_label: 'explain a thought becoming action',
        text: 'explain a thought becoming action',
      },
      {
        id: 'n1',
        node_key: 'nl_bridge|pattern|thought becoming action|confidence=0.95,inferred_cas=^9^O',
        kind: 'nl_bridge',
        role: 'pattern',
        label: 'thought becoming action',
        normalized_label: 'thought becoming action',
        axis_attrs: { confidence: 0.95, inferred_cas: '^9^O' },
        text: 'Matched the English request to a compact CAS expression.',
      },
      {
        id: 'n2',
        node_key: 'cas_expression|inferred|^9^o|',
        kind: 'cas_expression',
        role: 'inferred',
        label: '^9^O',
        normalized_label: '^9^o',
        text: 'Below/Effect in the Operational domain — a thought landing as behavior.',
      },
      {
        id: 'n3',
        node_key: 'model_generation|output|below/effect in the operational domain — a thought landing as behavior.|',
        kind: 'model_generation',
        role: 'output',
        label: 'thought landing as behavior',
        normalized_label: 'thought landing as behavior',
        text: 'Below/Effect in the Operational domain — a thought landing as behavior.',
      },
      {
        id: 'n4',
        node_key: 'slot_pattern|summary|only joining words generated|length=18,longest_stage_var_run=0,stage_var_count=0',
        kind: 'slot_pattern',
        role: 'summary',
        label: 'slot trace: plain explanation',
        normalized_label: 'slot trace: plain explanation',
        axis_attrs: {
          length: 18,
          longest_stage_var_run: 0,
          stage_var_count: 0,
        },
        text: 'The output is an identifier-free explanation, so every generated token stays in the plain-language slot.',
      },
      {
        id: 'n5',
        node_key: 'confidence_marker|strong|coverage: strong|band=strong',
        kind: 'confidence_marker',
        role: 'strong',
        label: 'coverage: strong',
        normalized_label: 'coverage: strong',
        axis_attrs: { band: 'strong' },
        text: 'No source identifiers were expected here, so there is no copy warning.',
      },
    ],
    edges: [
      {
        id: 'e0',
        edge_key:
          'user_prompt|input|explain a thought becoming action||nl_bridge|pattern|thought becoming action|confidence=0.95,inferred_cas=^9^O|parent_child|',
        source: 'n0',
        target: 'n1',
        source_key: 'user_prompt|input|explain a thought becoming action|',
        target_key: 'nl_bridge|pattern|thought becoming action|confidence=0.95,inferred_cas=^9^O',
        kind: 'parent_child',
      },
      {
        id: 'e1',
        edge_key:
          'nl_bridge|pattern|thought becoming action|confidence=0.95,inferred_cas=^9^O|cas_expression|inferred|^9^o||parent_child|',
        source: 'n1',
        target: 'n2',
        source_key: 'nl_bridge|pattern|thought becoming action|confidence=0.95,inferred_cas=^9^O',
        target_key: 'cas_expression|inferred|^9^o|',
        kind: 'parent_child',
      },
      {
        id: 'e2',
        edge_key:
          'cas_expression|inferred|^9^o||model_generation|output|below/effect in the operational domain — a thought landing as behavior.||parent_child|',
        source: 'n2',
        target: 'n3',
        source_key: 'cas_expression|inferred|^9^o|',
        target_key: 'model_generation|output|below/effect in the operational domain — a thought landing as behavior.|',
        kind: 'parent_child',
      },
      {
        id: 'e3',
        edge_key:
          'model_generation|output|below/effect in the operational domain — a thought landing as behavior.||slot_pattern|summary|only joining words generated|length=18,longest_stage_var_run=0,stage_var_count=0|parent_child|',
        source: 'n3',
        target: 'n4',
        source_key: 'model_generation|output|below/effect in the operational domain — a thought landing as behavior.|',
        target_key: 'slot_pattern|summary|only joining words generated|length=18,longest_stage_var_run=0,stage_var_count=0',
        kind: 'parent_child',
      },
      {
        id: 'e4',
        edge_key:
          'model_generation|output|below/effect in the operational domain — a thought landing as behavior.||confidence_marker|strong|coverage: strong|band=strong|parent_child|',
        source: 'n3',
        target: 'n5',
        source_key: 'model_generation|output|below/effect in the operational domain — a thought landing as behavior.|',
        target_key: 'confidence_marker|strong|coverage: strong|band=strong',
        kind: 'parent_child',
      },
    ],
    node_count: 6,
    edge_count: 5,
  },
};

export interface TraceLoaderProps {
  onTraceLoaded: (trace: AtlasTrace) => void;
  onError: (message: string) => void;
}

/** URL search-param name TraceLoader watches on mount. */
export const TRACE_QUERY_PARAM = 'trace';

/** Parse a string blob into an AtlasTrace or return an error message. */
export function parseTraceBlob(
  raw: string,
): { ok: true; trace: AtlasTrace } | { ok: false; error: string } {
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch (err) {
    const msg = err instanceof Error ? err.message : 'Unknown JSON parse error.';
    return { ok: false, error: `Could not parse JSON: ${msg}` };
  }
  return validateAtlasTrace(parsed);
}

export function TraceLoader({ onTraceLoaded, onError }: TraceLoaderProps) {
  const [dragActive, setDragActive] = useState(false);
  const [lastSource, setLastSource] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  // Stable refs to the callbacks so the URL-param effect can run exactly
  // once on mount without re-firing if the parent passes new function
  // identities on each render.
  const onTraceLoadedRef = useRef(onTraceLoaded);
  const onErrorRef = useRef(onError);
  useEffect(() => {
    onTraceLoadedRef.current = onTraceLoaded;
  }, [onTraceLoaded]);
  useEffect(() => {
    onErrorRef.current = onError;
  }, [onError]);

  const handleLoadedTrace = useCallback(
    (trace: AtlasTrace, sourceLabel: string) => {
      setLastSource(sourceLabel);
      onTraceLoadedRef.current(trace);
    },
    [],
  );

  const handleError = useCallback((msg: string) => {
    onErrorRef.current(msg);
  }, []);

  const loadFromBlob = useCallback(
    (raw: string, sourceLabel: string) => {
      const result = parseTraceBlob(raw);
      if (result.ok) {
        handleLoadedTrace(result.trace, sourceLabel);
      } else {
        handleError(result.error);
      }
    },
    [handleLoadedTrace, handleError],
  );

  // ── URL ?trace=<encoded JSON> on mount ──
  useEffect(() => {
    if (typeof window === 'undefined') return;
    try {
      const params = new URLSearchParams(window.location.search);
      const raw = params.get(TRACE_QUERY_PARAM);
      if (raw && raw.length > 0) {
        loadFromBlob(raw, 'URL parameter');
      }
    } catch {
      // Ignore — URLSearchParams should never throw, but defend anyway.
    }
    // Intentionally run once on mount only. loadFromBlob is stable.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Demo button ──
  const handleDemo = useCallback(() => {
    handleLoadedTrace(DEMO_TRACE, 'Bundled demo');
  }, [handleLoadedTrace]);

  // ── File reader helper ──
  const readFile = useCallback(
    (file: File) => {
      const reader = new FileReader();
      reader.onload = () => {
        const raw = typeof reader.result === 'string' ? reader.result : '';
        loadFromBlob(raw, `File: ${file.name}`);
      };
      reader.onerror = () => {
        handleError(`Could not read file "${file.name}".`);
      };
      reader.readAsText(file);
    },
    [loadFromBlob, handleError],
  );

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) readFile(file);
      // Reset the input so re-selecting the same file fires `change` again
      e.target.value = '';
    },
    [readFile],
  );

  // ── Drag-drop handlers ──
  const handleDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      e.stopPropagation();
      setDragActive(false);
      const file = e.dataTransfer.files?.[0];
      if (file) readFile(file);
    },
    [readFile],
  );

  return (
    <div
      data-testid="trace-loader"
      className="rounded-2xl border border-slate-700 bg-slate-900/60 p-6 shadow-lg"
    >
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-100">
          Load a CAS trace
        </h2>
        <span className="font-mono text-xs text-slate-400">
          schema {TRACE_SCHEMA_VERSION}
        </span>
      </div>

      <p className="mb-4 text-sm text-slate-300">
        Drop a <span className="font-mono text-cyan-300">.json</span> trace,
        pick a file, or load the bundled demo. Every trace shows what CAS
        read, what the model emitted, and which source references carried
        over.
      </p>

      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={handleDemo}
          className="rounded-lg bg-cyan-600 px-4 py-2 text-sm font-medium text-white shadow hover:bg-cyan-500 focus:outline-none focus:ring-2 focus:ring-cyan-400"
        >
          Load demo trace
        </button>

        <label className="inline-flex cursor-pointer items-center rounded-lg border border-slate-600 bg-slate-800 px-4 py-2 text-sm font-medium text-slate-100 hover:bg-slate-700 focus-within:ring-2 focus-within:ring-cyan-400">
          Choose file
          <input
            ref={fileInputRef}
            type="file"
            accept="application/json,.json"
            onChange={handleFileChange}
            data-testid="trace-file-input"
            className="sr-only"
          />
        </label>
      </div>

      <div
        data-testid="trace-dropzone"
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={
          'mt-4 flex h-28 items-center justify-center rounded-xl border-2 border-dashed text-sm transition-colors ' +
          (dragActive
            ? 'border-cyan-400 bg-cyan-500/10 text-cyan-100'
            : 'border-slate-600 bg-slate-900/30 text-slate-400')
        }
      >
        {dragActive
          ? 'Drop the trace file to load'
          : 'Or drag and drop a trace.json here'}
      </div>

      <p className="mt-3 font-mono text-xs text-slate-500">
        Tip: open this page with{' '}
        <code className="text-cyan-300">?trace=&lt;encoded JSON&gt;</code> to
        load a trace directly from the URL.
      </p>

      {lastSource && (
        <p
          data-testid="trace-loaded-source"
          className="mt-3 text-xs text-emerald-300"
        >
          Loaded from {lastSource}.
        </p>
      )}
    </div>
  );
}

export default TraceLoader;
