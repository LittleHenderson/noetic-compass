/**
 * Tests for TraceLoader — file/drop/URL/demo paths for loading a
 * traceability_v0 trace. Asserts the contract documented in the
 * atlas-v0 Agent B brief:
 *   - Demo button loads valid trace → onTraceLoaded
 *   - File picker with invalid JSON → onError
 *   - File picker with valid schema → onTraceLoaded
 *   - File picker missing required keys → onError
 *   - URL ?trace= parses correctly
 *   - File picker with wrong schema_version → onError
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, act } from '@testing-library/react';
import { TraceLoader, DEMO_TRACE } from './TraceLoader';
import { ThoughtTreeView, type ThoughtTree } from './ThoughtTreeView';
import { validateAtlasTrace, type AtlasTrace } from '../../lib/trace';

// ── Helpers ─────────────────────────────────────────────────────

function makeValidTraceJson(): string {
  return JSON.stringify(DEMO_TRACE);
}

/**
 * Drive the hidden <input type="file"> by attaching a File to it and
 * firing a synthetic `change` event. RTL's userEvent.upload also works
 * but this is the most portable form across vitest/jsdom versions.
 */
async function selectFile(input: HTMLInputElement, file: File) {
  Object.defineProperty(input, 'files', {
    value: [file],
    configurable: true,
  });
  await act(async () => {
    input.dispatchEvent(new Event('change', { bubbles: true }));
  });
}

beforeEach(() => {
  // Reset URL search params before every test — the URL effect runs on
  // mount, so we need a clean slate.
  window.history.replaceState({}, '', '/');
});

afterEach(() => {
  vi.restoreAllMocks();
});

// ── Demo button ─────────────────────────────────────────────────

describe('TraceLoader — demo button', () => {
  it('fires onTraceLoaded with a valid trace when clicked', async () => {
    const onTraceLoaded = vi.fn();
    const onError = vi.fn();
    render(
      <TraceLoader onTraceLoaded={onTraceLoaded} onError={onError} />,
    );
    const btn = screen.getByRole('button', { name: /load demo trace/i });
    await act(async () => {
      btn.click();
    });
    expect(onTraceLoaded).toHaveBeenCalledTimes(1);
    const trace = onTraceLoaded.mock.calls[0][0] as AtlasTrace;
    expect(trace.schema_version).toBe('traceability_v0');
    expect(onError).not.toHaveBeenCalled();
  });

  it('DEMO_TRACE passes the tightened validator (per-node id + edge keys)', () => {
    // REGRESSION PIN (Codex audit a658f6d blocker 2): the bundled
    // demo must pass the strict validator that requires every node to
    // carry id + node_key + kind + role + label + normalized_label,
    // and every edge to carry id + edge_key + source/target/keys.
    const result = validateAtlasTrace(DEMO_TRACE);
    expect(result.ok).toBe(true);
  });

  it('DEMO_TRACE renders nodes and edges in ThoughtTreeView', () => {
    // REGRESSION PIN (Codex audit a658f6d blocker 2): the demo button
    // was previously rendering blank because the nested root and child
    // lacked id/node_key, so ThoughtTreeView could not lay them out.
    // This test pins both halves of the contract: load the demo via
    // the button AND feed the resulting trace into ThoughtTreeView,
    // then assert real visible nodes + edges.
    let loaded: AtlasTrace | null = null;
    const { rerender } = render(
      <TraceLoader
        onTraceLoaded={(t) => {
          loaded = t;
        }}
        onError={() => {}}
      />,
    );
    const btn = screen.getByRole('button', { name: /load demo trace/i });
    act(() => {
      btn.click();
    });
    expect(loaded).not.toBeNull();
    if (!loaded) return;
    rerender(
      <ThoughtTreeView
        tree={(loaded as AtlasTrace).thought_tree as unknown as ThoughtTree}
      />,
    );
    // 2 flat nodes, 1 flat edge — exact counts pin against future
    // demo trims.
    const nodeGroups = document.querySelectorAll('[data-node-id]');
    expect(nodeGroups.length).toBe(2);
    const edges = document.querySelectorAll('[data-edge-id]');
    expect(edges.length).toBe(1);
    // Empty-state placeholder must NOT be rendered.
    expect(
      document.querySelector('[data-testid="thought-tree-empty"]'),
    ).toBeNull();
    // The user_prompt node should be present and labelled with the
    // CAS expression (may match more than once — SVG <title> + visible
    // text node both carry the label).
    expect(screen.getAllByText('^9^O').length).toBeGreaterThan(0);
  });

  it('DEMO_TRACE rationale uses Below/Effect language, not "Idea brought to Mind"', () => {
    // REGRESSION PIN (Codex audit a658f6d polish): the demo's
    // generated English must match the corrected ^9 = Below/Effect
    // rationale, not blend in ^0/^1 vocabulary.
    expect(DEMO_TRACE.output.english.toLowerCase()).toContain(
      'below/effect in the operational domain',
    );
    expect(DEMO_TRACE.output.english.toLowerCase()).toContain(
      'thought landing as behavior',
    );
    expect(DEMO_TRACE.output.english.toLowerCase()).not.toContain(
      'idea brought to mind',
    );
  });
});

// ── File picker ─────────────────────────────────────────────────

describe('TraceLoader — file picker', () => {
  it('fires onTraceLoaded for a valid schema', async () => {
    const onTraceLoaded = vi.fn();
    const onError = vi.fn();
    render(
      <TraceLoader onTraceLoaded={onTraceLoaded} onError={onError} />,
    );
    const input = screen.getByTestId('trace-file-input') as HTMLInputElement;
    const file = new File([makeValidTraceJson()], 'trace.json', {
      type: 'application/json',
    });
    await selectFile(input, file);
    await waitFor(() => expect(onTraceLoaded).toHaveBeenCalledTimes(1));
    expect(onError).not.toHaveBeenCalled();
  });

  it('fires onError when the JSON is invalid', async () => {
    const onTraceLoaded = vi.fn();
    const onError = vi.fn();
    render(
      <TraceLoader onTraceLoaded={onTraceLoaded} onError={onError} />,
    );
    const input = screen.getByTestId('trace-file-input') as HTMLInputElement;
    const file = new File(['{ not valid json'], 'broken.json', {
      type: 'application/json',
    });
    await selectFile(input, file);
    await waitFor(() => expect(onError).toHaveBeenCalledTimes(1));
    const msg = onError.mock.calls[0][0] as string;
    expect(msg.toLowerCase()).toMatch(/parse|json/);
    expect(onTraceLoaded).not.toHaveBeenCalled();
  });

  it('fires onError when required keys are missing', async () => {
    const onTraceLoaded = vi.fn();
    const onError = vi.fn();
    render(
      <TraceLoader onTraceLoaded={onTraceLoaded} onError={onError} />,
    );
    const input = screen.getByTestId('trace-file-input') as HTMLInputElement;
    // Drop `thought_tree`
    const trimmed: Record<string, unknown> = {
      ...(DEMO_TRACE as unknown as Record<string, unknown>),
    };
    delete trimmed.thought_tree;
    const file = new File([JSON.stringify(trimmed)], 'missing-key.json', {
      type: 'application/json',
    });
    await selectFile(input, file);
    await waitFor(() => expect(onError).toHaveBeenCalledTimes(1));
    expect(onError.mock.calls[0][0]).toContain('thought_tree');
    expect(onTraceLoaded).not.toHaveBeenCalled();
  });

  it('fires onError when schema_version is wrong', async () => {
    const onTraceLoaded = vi.fn();
    const onError = vi.fn();
    render(
      <TraceLoader onTraceLoaded={onTraceLoaded} onError={onError} />,
    );
    const input = screen.getByTestId('trace-file-input') as HTMLInputElement;
    const bad = { ...DEMO_TRACE, schema_version: 'trace_v0' };
    const file = new File([JSON.stringify(bad)], 'bad-version.json', {
      type: 'application/json',
    });
    await selectFile(input, file);
    await waitFor(() => expect(onError).toHaveBeenCalledTimes(1));
    expect(onError.mock.calls[0][0].toLowerCase()).toContain('schema_version');
    expect(onTraceLoaded).not.toHaveBeenCalled();
  });
});

// ── URL ?trace= param ───────────────────────────────────────────

describe('TraceLoader — URL ?trace= param', () => {
  it('parses a trace from the URL on mount', async () => {
    const encoded = encodeURIComponent(makeValidTraceJson());
    window.history.replaceState({}, '', `/?trace=${encoded}`);
    const onTraceLoaded = vi.fn();
    const onError = vi.fn();
    render(
      <TraceLoader onTraceLoaded={onTraceLoaded} onError={onError} />,
    );
    await waitFor(() => expect(onTraceLoaded).toHaveBeenCalledTimes(1));
    const trace = onTraceLoaded.mock.calls[0][0] as AtlasTrace;
    expect(trace.schema_version).toBe('traceability_v0');
    expect(onError).not.toHaveBeenCalled();
  });

  it('does nothing when no trace param is set', async () => {
    const onTraceLoaded = vi.fn();
    const onError = vi.fn();
    render(
      <TraceLoader onTraceLoaded={onTraceLoaded} onError={onError} />,
    );
    // Wait a microtask tick — nothing should fire
    await Promise.resolve();
    expect(onTraceLoaded).not.toHaveBeenCalled();
    expect(onError).not.toHaveBeenCalled();
  });
});
